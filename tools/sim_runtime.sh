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
python3 tools/prepare_px4_run.py --source-build "$SOURCE_BUILD" --output "$PX4_BUILD" --report "$RUN/px4-run-isolation.json"
python3 tools/stage_px4_debug_params.py --px4-build "$PX4_BUILD" --profile vio_closed_loop --output "$RUN/px4-params.json"
python3 tools/prepare_px4_vio_bootstrap_world.py --project-root /workspace \
  --px4-world /workspace/external/PX4-Autopilot/Tools/simulation/gz/worlds/default.sdf \
  --px4-server-config /workspace/external/PX4-Autopilot/src/modules/simulation/gz_bridge/server.config \
  --output "$RUN/vio_initialization.sdf" --report "$RUN/world.json"
python3 tools/check_imu_physics.py "$RUN"
cd "$PX4_BUILD"
source rootfs/gz_env.sh
export PX4_GZ_MODELS=/workspace/simulation/models
export PX4_GZ_WORLDS=/workspace/external/PX4-Autopilot/Tools/simulation/gz/worlds
export PX4_GZ_SERVER_CONFIG=/workspace/external/PX4-Autopilot/src/modules/simulation/gz_bridge/server.config
export PX4_GZ_PLUGINS="$SOURCE_BUILD/src/modules/simulation/gz_plugins"
export LD_LIBRARY_PATH="$SOURCE_BUILD/OpticalFlow/install/lib:$PX4_GZ_PLUGINS:${LD_LIBRARY_PATH:-}"
export GZ_SIM_RESOURCE_PATH="/workspace/simulation/models:${GZ_SIM_RESOURCE_PATH:-}"
export GZ_SIM_SYSTEM_PLUGIN_PATH="$PX4_GZ_PLUGINS:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
start gazebo-server env EGL_PLATFORM=surfaceless gz sim -s -r --headless-rendering "$RUN/vio_initialization.sdf"
READY=0
for ((i=0;i<40;i++)); do
  if gz service -l 2>/dev/null | grep -Fxq '/world/vio_initialization/create'; then READY=1; break; fi
  sleep 1
done
[[ "$READY" == 1 ]] || { echo 'Gazebo startup timeout' >&2; exit 10; }
SPAWN=$(python3 -c 'import json; print(json.load(open("/workspace/config/runtime.json"))["spawn_pose"])')
start px4 env PX4_SIMULATOR=gz PX4_SYS_AUTOSTART=5011 PX4_SIM_MODEL=gz_x500_d435i PX4_GZ_WORLD=vio_initialization PX4_GZ_MODEL_POSE="$SPAWN" HEADLESS=1 ./bin/px4 -d -w "$PX4_BUILD"
start agent /workspace/install/microxrcedds_agent/bin/MicroXRCEAgent udp4 -p 8888
cd /workspace
python3 tools/wait_sim_imu_settled.py --output "$RUN/settled-imu.json"
python3 tools/audit_px4_boot.py "$RUN"
SENSOR_BRIDGE_ARGS=()
if [[ -n "${D435I_SENSOR_BRIDGE_CONFIG:-}" ]]; then
  SENSOR_BRIDGE_ARGS+=("sensor_bridge_config:=$D435I_SENSOR_BRIDGE_CONFIG")
fi
start vio ros2 launch uav_px4_bridge vio_closed_loop_ego_px4.launch.py \
  project_root:=/workspace run_id:="$RUN_ID-stack" "${SENSOR_BRIDGE_ARGS[@]}"
SESSION=/workspace/artifacts/runs/$RUN_ID-stack/session/session.json
for ((i=0;i<90;i++)); do [[ ! -f "$SESSION" ]] || break; sleep 1; done
[[ -f "$SESSION" ]] || { echo 'VINS session creation timeout' >&2; exit 11; }
if [[ "${PROJECT_GUI:-0}" == 1 ]]; then
  python3 tools/prepare_mapping_rviz.py --session "$SESSION" --output "$RUN/mapping.rviz"
  start rviz bash tools/run_gpu_viewer.sh rviz -d "$RUN/mapping.rviz" --ros-args -p use_sim_time:=true
  start gazebo-gui bash tools/run_gpu_viewer.sh gazebo
fi
touch "$RUN/stack-started"
while kill -0 "${PIDS[0]}" 2>/dev/null; do sleep 5; done
