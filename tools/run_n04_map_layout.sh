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
[[ "$N04_MODE" == motion || "$N04_MODE" == static || "$N04_MODE" == motion_n06 ]] || { echo 'Capture mode must be motion, static, or motion_n06' >&2; exit 2; }
N06_PROFILE_INPUT=${5:-config/components/simulation/n06_observation_sweep.json}
N06_PROFILE_ABS=$(realpath -e -- "$N06_PROFILE_INPUT")
case "$N06_PROFILE_ABS" in
  "$PROJECT_ROOT"/*) N06_PROFILE_REL=${N06_PROFILE_ABS#"$PROJECT_ROOT"/} ;;
  *) echo 'N06 profile must be inside the project workspace' >&2; exit 2 ;;
esac
python3 - "$N06_PROFILE_ABS" <<'PY'
import json,sys
profile=json.load(open(sys.argv[1]))
required={'initial_hold_seconds','phase_seconds','world_acceleration_and_angular_acceleration',
          'phase_signs','stop_seconds','wall_timeout_seconds','command_period_seconds'}
if not required.issubset(profile):
    raise SystemExit('N06 profile is missing required motion fields')
if len(profile['world_acceleration_and_angular_acceleration']) != 6 or any(
        len(row) != 6 for row in profile['phase_signs']):
    raise SystemExit('N06 profile must define six-axis acceleration and signs')
PY
N04_RUN_DIR="$PROJECT_ROOT/artifacts/runs/$N04_RUN_ID"
[[ ! -e "$N04_RUN_DIR" ]] || { echo "Refusing to overwrite $N04_RUN_DIR" >&2; exit 9; }
[[ -z "$(docker ps -q --filter "label=d435i.project=$PROJECT_ROOT")" ]] || { echo 'Stop active project containers before N04 capture' >&2; exit 9; }
N04_IMAGE=$(python3 -c 'import json; print(json.load(open("config/runtime.json"))["image"])')
N04_EXPECTED_IMAGE=$(python3 -c 'import json; print(json.load(open("config/runtime.json"))["image_id"])')
N04_ACTUAL_IMAGE=$(docker image inspect "$N04_IMAGE" --format '{{.Id}}' 2>/dev/null || true)
[[ "$N04_ACTUAL_IMAGE" == "$N04_EXPECTED_IMAGE" ]] || { echo 'Fixed N04 container image is missing or mismatched' >&2; exit 10; }

mkdir -p "$N04_RUN_DIR/snapshots"
if [[ "$N04_MODE" == motion_n06 ]]; then
  python3 "$PROJECT_ROOT/tools/prepare_n04_mapping_world.py" --layout "$N04_LAYOUT" \
    --world "$N04_RUN_DIR/world.sdf" --truth-sdf "$N04_RUN_DIR/truth-scene.sdf" \
    --manifest "$N04_RUN_DIR/world-manifest.json" --n06-observation-surround \
    > "$N04_RUN_DIR/world-generation.json"
else
  python3 "$PROJECT_ROOT/tools/prepare_n04_mapping_world.py" --layout "$N04_LAYOUT" \
    --world "$N04_RUN_DIR/world.sdf" --truth-sdf "$N04_RUN_DIR/truth-scene.sdf" \
    --manifest "$N04_RUN_DIR/world-manifest.json" \
    > "$N04_RUN_DIR/world-generation.json"
fi
python3 - "$N04_RUN_DIR/run-inputs.json" "$N04_RUN_ID" "$N04_LAYOUT" "$N04_DOMAIN" "$N04_MODE" "$N06_PROFILE_REL" <<'PY'
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
    'tools/analyze_n06_snapshot_sweep.py',
    'tools/probe_n06_live_layout.py',
    'tools/run_sensor_motion.py',
    'tools/evaluate_n04_map_geometry.py',
    'tools/test_n04_map_geometry.py',
    'config/components/simulation/n04_geometry_layouts.json',
    'config/components/simulation/sensor_motion.json',
    'config/components/simulation/n06_observation_sweep.json',
    'config/components/mapping/ego_input.json',
    'config/components/mapping/ego_planner.json',
    'config/components/navigation/vehicle_envelope.json',
    'dependencies/sources.json',
    'dependencies/patches/ego/0039-full-curve-admission.patch',
    'dependencies/patches/ego/0041-n06-terminal-hold-admission.patch',
    'dependencies/patches/ego/0042-query-last-completed-fusion.patch',
    'dependencies/patches/ego/0043-n06-emergency-hold-fallback.patch',
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
profile_rel=sys.argv[6]
if profile_rel not in tool_files:
    tool_files.append(profile_rel)
surround_rel='simulation/models/n06_observation_surround/model.sdf'
surround_config_rel='simulation/models/n06_observation_surround/model.config'
if sys.argv[5]=='motion_n06':
    tool_files.extend([surround_rel, surround_config_rel])
hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in tool_files}
Path(sys.argv[1]).write_text(json.dumps({
    'schema':'n04-map-layout-run-inputs/v1',
    'run_id':sys.argv[2], 'layout_id':sys.argv[3],
    'ros_domain_id':int(sys.argv[4]), 'capture_mode':sys.argv[5],
    'n06_observation_profile':{'path':profile_rel,'sha256':hashes[profile_rel]},
    'n06_observation_surround':({
        'included':True, 'path':surround_rel, 'sha256':hashes[surround_rel],
        'model_config_sha256':hashes[surround_config_rel],
    } if sys.argv[5]=='motion_n06' else {'included':False}),
    'control_scope':('no PX4/bridge/control; one planner-only EGO diagnostic goal'
                     if sys.argv[5] in ('static', 'motion_n06') else
                     'no PX4/bridge/control/navigation goal'),
    'container_image':json.load(open('config/runtime.json'))['image_id'],
    'toolchain_sha256':hashes,
},indent=2)+'\n')
PY

N04_CONTAINER="d435i-$N04_RUN_ID"
# Keep a generous grace period for Python recorders to flush compressed input
# arrays and motion truth after a diagnostic run is interrupted.
cleanup_container() { docker stop -t 90 "$N04_CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup_container EXIT INT TERM
docker run --rm --init --name "$N04_CONTAINER" --label "d435i.project=$PROJECT_ROOT" \
  --gpus all --network host --ipc host --shm-size=512m \
  -e ROS_DOMAIN_ID="$N04_DOMAIN" -e ROS_LOCALHOST_ONLY=0 \
  -e GZ_IP=127.0.0.1 -e "GZ_PARTITION=d435i_n04_$N04_RUN_ID" \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -v "$PROJECT_ROOT:/workspace:rw" -w /workspace "$N04_IMAGE" \
  bash /workspace/tools/run_n04_map_layout_container.sh "$N04_RUN_ID" "$N04_LAYOUT" "$N04_MODE" "/workspace/$N06_PROFILE_REL"
