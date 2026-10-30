#!/usr/bin/env bash
# Starts sensors/localization/mapping/planning; never enables or arms the bridge.
set -Ee -o pipefail
cd /workspace
RUN_ID=${1:?run id required}
RUN=/workspace/artifacts/runs/$RUN_ID
export FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/config/middleware/fastdds_local_shm.xml
export QT_QPA_PLATFORM=xcb __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
export VINS_DIAGNOSTIC_COST_GROUPS=${VINS_DIAGNOSTIC_COST_GROUPS:-1}
case "$VINS_DIAGNOSTIC_COST_GROUPS" in 1|continuous) ;; *) echo 'Invalid VINS diagnostic mode' >&2; exit 2;; esac
python3 -c 'import json,os,sys; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps({"cost_groups_mode":os.environ["VINS_DIAGNOSTIC_COST_GROUPS"],"scope":"read-only Ceres residual evaluation; no health or control changes"},indent=2)+"\n")' "$RUN/vins-diagnostics.json"
source /opt/ros/jazzy/setup.bash
source /workspace/install/local_setup.bash
SOURCE_BUILD=/workspace/$(python3 -c 'import json; print(json.load(open("config/runtime.json"))["px4_build"])')
PX4_BUILD="$RUN/px4_sitl_default"
PIDS=()
start() { local label=$1; shift; setsid "$@" > "$RUN/$label.log" 2>&1 & PIDS+=("$!"); }
cleanup() {
  trap - EXIT INT TERM
  for pid in "${PIDS[@]}"; do kill -INT -- "-$pid" 2>/dev/null || true; done
  sleep 2
  for pid in "${PIDS[@]}"; do kill -TERM -- "-$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM
nvidia-smi -L > "$RUN/gpu.txt"
python3 tools/runtime_manifest.py "$RUN/runtime-contract.json"
if [[ "${D435I_N10_CAPTURE:-0}" == 1 ]]; then
  python3 - "$RUN" "$RUN_ID" <<'PY' || echo 'Optional sensor-capture launch manifest could not be written; continue with offline evidence marked insufficient.' > "$RUN/n10-capture-launch-manifest-error.txt"
import hashlib
import json
import sys
from pathlib import Path
run, run_id = Path(sys.argv[1]), sys.argv[2]
root = Path('/workspace')
capture_path = root / 'config/n10_capture.json'
capture = json.loads(capture_path.read_text())
sensor_path = root / capture['sensor_config']
sensor = json.loads(sensor_path.read_text())
runtime = json.loads((run / 'runtime-contract.json').read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
record = {
    'schema': 'n10-capture-launch-manifest/v1',
    'run_id': run_id,
    'runtime_contract_sha256': runtime['sha256'],
    'n10_capture': {
        'enabled': True,
        'capture_config': capture_path.relative_to(root).as_posix(),
        'capture_config_sha256': digest(capture_path),
        'sensor_config': capture['sensor_config'],
        'sensor_config_sha256': digest(sensor_path),
        'resolved_topics': {
            'stereo_left_image': sensor[capture['sensor_streams']['stereo_left_image']],
            'stereo_right_image': sensor[capture['sensor_streams']['stereo_right_image']],
            'camera_imu': sensor[capture['sensor_streams']['camera_imu']],
        },
        'recorder_sha256': digest(root / 'tools/diagnostics/record_n10_sensor_streams.py'),
        'resource_observer_sha256': digest(root / 'tools/diagnostics/record_n10_resources.py'),
        'evaluator_sha256': digest(root / 'tools/debug_truth/evaluate_n10_sensor_capture.py'),
        'runtime_effect': False,
    },
}
(run / 'n10-capture-launch-manifest.json').write_text(
    json.dumps(record, indent=2) + '\n')
PY
fi
python3 tools/prepare_px4_run.py --source-build "$SOURCE_BUILD" --output "$PX4_BUILD" --report "$RUN/px4-run-isolation.json"
python3 tools/stage_px4_debug_params.py --px4-build "$PX4_BUILD" --profile vio_closed_loop --output "$RUN/px4-params.json"
python3 tools/prepare_px4_vio_bootstrap_world.py --project-root /workspace \
  --px4-world /workspace/external/PX4-Autopilot/Tools/simulation/gz/worlds/default.sdf \
  --px4-server-config /workspace/external/PX4-Autopilot/src/modules/simulation/gz_bridge/server.config \
  --output "$RUN/vio_initialization.sdf" --report "$RUN/world.json" --scene "${D435I_SCENE:-room}"
python3 tools/check_imu_physics.py "$RUN"
cd "$PX4_BUILD"
source rootfs/gz_env.sh
export PX4_GZ_MODELS=/workspace/simulation/models
export PX4_GZ_WORLDS=/workspace/external/PX4-Autopilot/Tools/simulation/gz/worlds
export PX4_GZ_SERVER_CONFIG=/workspace/external/PX4-Autopilot/src/modules/simulation/gz_bridge/server.config
export PX4_GZ_PLUGINS="$SOURCE_BUILD/src/modules/simulation/gz_plugins"
export LD_LIBRARY_PATH="$SOURCE_BUILD/OpticalFlow/install/lib:$PX4_GZ_PLUGINS:${LD_LIBRARY_PATH:-}"
N09_CONTACTS=${D435I_N09_CONTACTS:-0}
case "$N09_CONTACTS" in
  0) export GZ_SIM_RESOURCE_PATH="/workspace/simulation/models:${GZ_SIM_RESOURCE_PATH:-}" ;;
  1)
    KINEMATICS_ARGS=()
    if [[ "${D435I_N10_KINEMATICS:-0}" == 1 ]]; then KINEMATICS_ARGS+=(--kinematics); fi
    python3 /workspace/tools/prepare_n09_contact_model.py \
      --output "$RUN/n09-contact-models" \
      --report "$RUN/n09-contact-model-manifest.json" "${KINEMATICS_ARGS[@]}"
    export GZ_SIM_RESOURCE_PATH="$RUN/n09-contact-models:/workspace/simulation/models:${GZ_SIM_RESOURCE_PATH:-}"
    # PX4's gzsim startup constructs a direct file:// URI from
    # PX4_GZ_MODELS/<model>/model.sdf. GZ_SIM_RESOURCE_PATH alone cannot
    # select the run-local root wrapper, so point PX4 at that overlay only
    # when it contains the optional read-only kinematics plugin.
    if [[ "${D435I_N10_KINEMATICS:-0}" == 1 ]]; then
      export PX4_GZ_MODELS="$RUN/n09-contact-models"
    fi
    ;;
  *) echo 'D435I_N09_CONTACTS must be 0 or 1' >&2; exit 2 ;;
esac
export GZ_SIM_SYSTEM_PLUGIN_PATH="$PX4_GZ_PLUGINS:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
python3 - "$RUN" "$PX4_GZ_MODELS" x500_d435i "${D435I_N10_KINEMATICS:-0}" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

run = Path(sys.argv[1]).resolve()
models_root = Path(sys.argv[2]).resolve()
model_name = sys.argv[3]
kinematics_requested = sys.argv[4] == '1'
model_path = models_root / model_name / 'model.sdf'
plugin_count = 0
parse_error = None
try:
    root = ET.parse(model_path).getroot()
    plugin_count = sum(
        plugin.get('filename') == 'libuav_truth_kinematics.so'
        and plugin.get('name') == 'uav::debug_truth::ModelKinematics'
        for plugin in root.findall('./model/plugin'))
except (OSError, ET.ParseError) as exc:
    parse_error = f'{type(exc).__name__}:{exc}'
record = {
    'schema': 'n10-px4-gazebo-model-source/v1',
    'classification': 'run identity evidence only; no admission or control effect',
    'selection_mechanism': 'PX4 px4-rc.gzsim direct file URI from PX4_GZ_MODELS',
    'model_name': model_name,
    'px4_gz_models': str(models_root),
    'selected_model_sdf': str(model_path),
    'selected_model_sdf_sha256': (
        hashlib.sha256(model_path.read_bytes()).hexdigest()
        if model_path.is_file() else None),
    'kinematics_requested': kinematics_requested,
    'kinematics_plugin_entries': plugin_count,
    'kinematics_plugin_source_present': plugin_count == 1,
    'sdf_parse_error': parse_error,
}
(run / 'n10-px4-model-source.json').write_text(
    json.dumps(record, indent=2) + '\n', encoding='utf-8')
PY
start gazebo-server env EGL_PLATFORM=surfaceless gz sim -s -r --headless-rendering "$RUN/vio_initialization.sdf"
READY=0
for ((i=0;i<40;i++)); do
  if gz service -l 2>/dev/null | grep -Fxq '/world/vio_initialization/create'; then READY=1; break; fi
  sleep 1
done
[[ "$READY" == 1 ]] || { echo 'Gazebo startup timeout' >&2; exit 10; }
SPAWN=$(python3 /workspace/tools/resolve_sim_spawn.py --project-root /workspace \
  --config "${D435I_SPAWN_CONFIG:-}" --scene "${D435I_SCENE:-room}" --report "$RUN/spawn-pose.json")
start px4 env PX4_SIMULATOR=gz PX4_SYS_AUTOSTART=5011 PX4_SIM_MODEL=gz_x500_d435i PX4_GZ_WORLD=vio_initialization PX4_GZ_MODEL_POSE="$SPAWN" HEADLESS=1 ./bin/px4 -d -w "$PX4_BUILD"
start agent /workspace/install/microxrcedds_agent/bin/MicroXRCEAgent udp4 -p 8888
cd /workspace
python3 tools/wait_sim_imu_settled.py --output "$RUN/settled-imu.json"
python3 tools/audit_px4_boot.py "$RUN"
SENSOR_BRIDGE_ARGS=()
if [[ -n "${D435I_SENSOR_BRIDGE_CONFIG:-}" ]]; then
  SENSOR_BRIDGE_ARGS+=("sensor_bridge_config:=$D435I_SENSOR_BRIDGE_CONFIG")
fi
PLANNER_ARGS=()
if [[ -n "${D435I_PLANNER_CONFIG:-}" ]]; then
  PLANNER_ARGS+=("planner_config:=$D435I_PLANNER_CONFIG")
fi
N08_MODE=${D435I_N08_MODE:-execute}
case "$N08_MODE" in
  hold|compute_only|execute) ;;
  *) echo 'D435I_N08_MODE must be hold, compute_only, or execute' >&2; exit 2 ;;
esac
if [[ "${D435I_N10_CAPTURE:-0}" == 1 ]]; then
  # Subscribe before launching VINS; evidence capture never gates the flight task.
  CAPTURE_MAX_WALL_S=${D435I_N10_CAPTURE_WALL_S:-3600}
  start n10-sensor-capture python3 tools/diagnostics/record_n10_sensor_streams.py \
    "$RUN" --max-wall-s "$CAPTURE_MAX_WALL_S"
  start n10-resources python3 tools/diagnostics/record_n10_resources.py \
    "$RUN" --max-wall-s "$CAPTURE_MAX_WALL_S"
fi
N10_DEPTH_FAULT=${D435I_N10_DEPTH_FAULT:-0}
case "$N10_DEPTH_FAULT" in
  0) ;;
  1)
    EXPECTED_DEPTH_BRIDGE=/workspace/config/components/simulation/n03_depth_fault_bridge.yaml
    [[ "${D435I_SENSOR_BRIDGE_CONFIG:-}" == "$EXPECTED_DEPTH_BRIDGE" ]] || {
      echo 'N10 depth fault injection requires the isolated n03_depth_fault_bridge.yaml route' >&2
      exit 12
    }
    DROP_AFTER_GOAL_S=${D435I_N10_DEPTH_FAULT_AFTER_GOAL_S:-2.0}
    DROP_DURATION_S=${D435I_N10_DEPTH_FAULT_DURATION_S:-3.0}
    python3 - "$DROP_AFTER_GOAL_S" "$DROP_DURATION_S" "$RUN" <<'PYDEPTH'
import hashlib
import json
import math
import sys
from pathlib import Path
after, duration = map(float, sys.argv[1:3])
if not math.isfinite(after) or after < 0 or not math.isfinite(duration) or duration <= 0:
    raise SystemExit('N10 depth fault schedule must use finite non-negative start and positive duration')
root = Path('/workspace')
bridge = root / 'config/components/simulation/n03_depth_fault_bridge.yaml'
report = {
    'schema': 'n10-depth-fault-injection-config/v1',
    'classification': 'explicit diagnostic input fault; no runtime health gate',
    'bridge_config_path': bridge.relative_to(root).as_posix(),
    'bridge_config_sha256': hashlib.sha256(bridge.read_bytes()).hexdigest(),
    'relay_path': 'tools/fault_relay.py',
    'relay_sha256': hashlib.sha256((root / 'tools/fault_relay.py').read_bytes()).hexdigest(),
    'drop_start_after_active_goal_source_stamp_s': after,
    'drop_duration_source_s': duration,
    'input_topic': '/fault/input/depth',
    'output_topic': '/sensors/d435i/depth',
    'unaffected_direct_inputs': [
        '/sensors/d435i/infra1/image_rect',
        '/sensors/d435i/infra2/image_rect',
        '/sensors/d435i/imu',
    ],
    'control_published': False,
    'takeoff_refusal_added': False,
}
(Path(sys.argv[3]) / 'n10-depth-fault-injection-config.json').write_text(
    json.dumps(report, indent=2) + '\n')
PYDEPTH
    start n10-depth-fault-relay python3 tools/fault_relay.py \
      --kind depth --after-goal-s "$DROP_AFTER_GOAL_S" \
      --drop-for-source-s "$DROP_DURATION_S" \
      --duration-wall-s "${D435I_N10_CAPTURE_WALL_S:-3600}" \
      --report "$RUN/n10-depth-fault-relay.json"
    printf '%s\n' "$!" > "$RUN/n10-depth-fault-relay.pid"
    ;;
  *) echo 'D435I_N10_DEPTH_FAULT must be 0 or 1' >&2; exit 2 ;;
esac
start vio ros2 launch uav_px4_bridge vio_closed_loop_ego_px4.launch.py \
  project_root:=/workspace run_id:="$RUN_ID-stack" \
  enable_visualization:="${PROJECT_GUI:-0}" \
  n08_mode:="$N08_MODE" \
  "${PLANNER_ARGS[@]}" "${SENSOR_BRIDGE_ARGS[@]}"
SESSION=/workspace/artifacts/runs/$RUN_ID-stack/session/session.json
for ((i=0;i<90;i++)); do [[ ! -f "$SESSION" ]] || break; sleep 1; done
[[ -f "$SESSION" ]] || { echo 'VINS session creation timeout' >&2; exit 11; }
if [[ "$N10_DEPTH_FAULT" == 1 ]]; then
  DEPTH_FAULT_ROUTE_READY=0
  for ((i=0;i<40;i++)); do
    if ros2 topic info /fault/input/depth --verbose > "$RUN/n10-depth-fault-input-graph.txt" 2>&1 \
        && grep -Fxq 'Publisher count: 1' "$RUN/n10-depth-fault-input-graph.txt" \
        && grep -Fxq 'Subscription count: 1' "$RUN/n10-depth-fault-input-graph.txt" \
        && ros2 topic info /sensors/d435i/depth --verbose > "$RUN/n10-depth-fault-output-graph.txt" 2>&1 \
        && grep -Fxq 'Publisher count: 1' "$RUN/n10-depth-fault-output-graph.txt"; then
      DEPTH_FAULT_ROUTE_READY=1
      break
    fi
    sleep 0.5
  done
  [[ "$DEPTH_FAULT_ROUTE_READY" == 1 ]] || {
    echo 'Isolated depth fault relay route is not active; no goal was sent' >&2
    exit 13
  }
fi
if [[ "${PROJECT_GUI:-0}" == 1 ]]; then
  python3 tools/prepare_mapping_rviz.py --session "$SESSION" --output "$RUN/mapping.rviz"
  start rviz bash tools/run_gpu_viewer.sh rviz -d "$RUN/mapping.rviz" --ros-args -p use_sim_time:=true
  start gazebo-gui bash tools/run_gpu_viewer.sh gazebo
fi
touch "$RUN/stack-started"
while kill -0 "${PIDS[0]}" 2>/dev/null; do sleep 5; done
