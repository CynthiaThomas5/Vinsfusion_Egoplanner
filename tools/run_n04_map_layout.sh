#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PROJECT_ROOT"
N04_RUN_ID=${1:?Usage: run_n04_map_layout.sh RUN_ID wall_box_column|corridor_box_column ROS_DOMAIN_ID}
N04_LAYOUT=${2:?Specify wall_box_column or corridor_box_column}
N04_DOMAIN=${3:?Specify a dedicated ROS_DOMAIN_ID}
N04_MODE=${4:-motion}
[[ "$N04_RUN_ID" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$ ]] || { echo 'Invalid run id' >&2; exit 2; }
[[ "$N04_LAYOUT" == wall_box_column || "$N04_LAYOUT" == corridor_box_column ]] || { echo 'Invalid N04 layout' >&2; exit 2; }
[[ "$N04_DOMAIN" =~ ^[0-9]+$ ]] && ((N04_DOMAIN >= 0 && N04_DOMAIN <= 232)) || { echo 'ROS_DOMAIN_ID must be between 0 and 232' >&2; exit 2; }
[[ "$N04_MODE" == motion || "$N04_MODE" == static ]] || { echo 'Capture mode must be motion or static' >&2; exit 2; }
N04_RUN_DIR="$PROJECT_ROOT/artifacts/runs/$N04_RUN_ID"
[[ ! -e "$N04_RUN_DIR" ]] || { echo "Refusing to overwrite $N04_RUN_DIR" >&2; exit 9; }
[[ -z "$(docker ps -q --filter "label=d435i.project=$PROJECT_ROOT")" ]] || { echo 'Stop active project containers before N04 capture' >&2; exit 9; }
N04_IMAGE=$(python3 -c 'import json; print(json.load(open("config/runtime.json"))["image"])')
N04_EXPECTED_IMAGE=$(python3 -c 'import json; print(json.load(open("config/runtime.json"))["image_id"])')
N04_ACTUAL_IMAGE=$(docker image inspect "$N04_IMAGE" --format '{{.Id}}' 2>/dev/null || true)
[[ "$N04_ACTUAL_IMAGE" == "$N04_EXPECTED_IMAGE" ]] || { echo 'Fixed N04 container image is missing or mismatched' >&2; exit 10; }

mkdir -p "$N04_RUN_DIR/snapshots"
python3 "$PROJECT_ROOT/tools/prepare_n04_mapping_world.py" --layout "$N04_LAYOUT" \
  --world "$N04_RUN_DIR/world.sdf" --truth-sdf "$N04_RUN_DIR/truth-scene.sdf" \
  --manifest "$N04_RUN_DIR/world-manifest.json" > "$N04_RUN_DIR/world-generation.json"
python3 - "$N04_RUN_DIR/run-inputs.json" "$N04_RUN_ID" "$N04_LAYOUT" "$N04_DOMAIN" "$N04_MODE" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path.cwd()
tool_files=[
    'tools/run_n04_map_layout.sh',
    'tools/run_n04_map_layout_container.sh',
    'tools/n04_mapping_stack.launch.py',
    'tools/prepare_n04_mapping_world.py',
    'tools/wait_n04_ready.py',
    'tools/record_n04_mapping_inputs.py',
    'tools/capture_live_occupancy_snapshot.py',
    'tools/run_sensor_motion.py',
    'tools/evaluate_n04_map_geometry.py',
    'tools/test_n04_map_geometry.py',
    'config/components/simulation/n04_geometry_layouts.json',
    'config/components/simulation/sensor_motion.json',
    'config/components/mapping/ego_input.json',
    'config/components/mapping/ego_planner.json',
    'config/components/navigation/vehicle_envelope.json',
    'dependencies/sources.json',
    'dependencies/patches/ego/0039-full-curve-admission.patch',
    'dependencies/patches/ego/0041-n06-terminal-hold-admission.patch',
    'simulation/models/d435i/model.sdf',
    'src/own/uav_mapping/uav_mapping/adapter.py',
    'src/own/uav_mapping/uav_mapping/mapping_input.py',
    'src/own/uav_px4_bridge/uav_px4_bridge/vio_ego_bringup.py',
    'src/vendor/ego_planner/planner/plan_env/src/grid_map.cpp',
    'src/vendor/ego_planner/planner/plan_env/include/plan_env/grid_map.h',
    'src/vendor/ego_planner/planner/plan_env/include/plan_env/swept_curve.h',
    'src/vendor/ego_planner/planner/plan_manage/src/ego_replan_fsm.cpp',
    'src/vendor/ego_planner/planner/plan_manage/launch/advanced_param.launch.py',
    'src/vendor/ego_planner/planner/plan_env/src/raycast.cpp',
]
hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in tool_files}
Path(sys.argv[1]).write_text(json.dumps({
    'schema':'n04-map-layout-run-inputs/v1',
    'run_id':sys.argv[2], 'layout_id':sys.argv[3],
    'ros_domain_id':int(sys.argv[4]), 'capture_mode':sys.argv[5],
    'control_scope':'no PX4/bridge/control/navigation goal',
    'container_image':json.load(open('config/runtime.json'))['image_id'],
    'toolchain_sha256':hashes,
},indent=2)+'\n')
PY

N04_CONTAINER="d435i-$N04_RUN_ID"
cleanup_container() { docker stop -t 15 "$N04_CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup_container EXIT INT TERM
docker run --rm --init --name "$N04_CONTAINER" --label "d435i.project=$PROJECT_ROOT" \
  --gpus all --network host --ipc host --shm-size=512m \
  -e ROS_DOMAIN_ID="$N04_DOMAIN" -e ROS_LOCALHOST_ONLY=0 \
  -e GZ_IP=127.0.0.1 -e "GZ_PARTITION=d435i_n04_$N04_RUN_ID" \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -v "$PROJECT_ROOT:/workspace:rw" -w /workspace "$N04_IMAGE" \
  bash /workspace/tools/run_n04_map_layout_container.sh "$N04_RUN_ID" "$N04_LAYOUT" "$N04_MODE"
