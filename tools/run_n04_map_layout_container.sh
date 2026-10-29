#!/usr/bin/env bash
set -Eeuo pipefail
cd /workspace
RUN_ID=${1:?run id required}
LAYOUT_ID=${2:?layout id required}
MODE=${3:-motion}
N06_PROFILE=${4:-/workspace/config/components/simulation/n06_observation_sweep.json}
[[ "$MODE" == motion || "$MODE" == static || "$MODE" == motion_n06 ]] || { echo 'Invalid capture mode' >&2; exit 2; }
[[ "$N06_PROFILE" == /workspace/* && -f "$N06_PROFILE" ]] || { echo 'Invalid workspace N06 profile' >&2; exit 2; }
WORLD=/workspace/artifacts/runs/$RUN_ID/world.sdf
RUN=/workspace/artifacts/runs/$RUN_ID
STACK_ID=${RUN_ID}-stack
set +u
source /opt/ros/jazzy/setup.bash
source /workspace/install/local_setup.bash
set -u
export FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/config/middleware/fastdds_local_shm.xml
export GZ_SIM_RESOURCE_PATH=/workspace/simulation/models:${GZ_SIM_RESOURCE_PATH:-}
export GZ_SIM_SYSTEM_PLUGIN_PATH=${GZ_SIM_SYSTEM_PLUGIN_PATH:-}
export QT_QPA_PLATFORM=xcb
export EGL_PLATFORM=surfaceless
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json

LAUNCH_PID=
MOTION_PID=
RECORDER_PID=
stop_group() {
  local pid=${1:-}
  [[ -n "$pid" ]] || return 0
  kill -0 "$pid" 2>/dev/null || { wait "$pid" 2>/dev/null || true; return 0; }
  kill -INT -- "-$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}
cleanup() {
  trap - EXIT INT TERM
  # The motion process clears its persistent wrench from its own finally block.
  stop_group "$MOTION_PID"
  stop_group "$RECORDER_PID"
  stop_group "$LAUNCH_PID"
}
on_signal() { exit 130; }
trap cleanup EXIT
trap on_signal INT TERM

setsid ros2 launch /workspace/tools/n04_mapping_stack.launch.py \
  project_root:=/workspace run_id:="$STACK_ID" world:="$WORLD" \
  > "$RUN/mapping-stack.log" 2>&1 &
LAUNCH_PID=$!

for ((attempt=0; attempt<90; ++attempt)); do
  kill -0 "$LAUNCH_PID" 2>/dev/null || {
    tail -n 120 "$RUN/mapping-stack.log" >&2
    exit 10
  }
  [[ -f "/workspace/artifacts/runs/$STACK_ID/session/session.json" ]] && break
  sleep 1
done
SESSION=/workspace/artifacts/runs/$STACK_ID/session/session.json
[[ -f "$SESSION" ]] || { echo 'VINS session creation timed out' >&2; exit 11; }
N04_EPOCH=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["epoch"])' "$SESSION")
python3 tools/runtime_manifest.py "$RUN/runtime-contract.json"

READY_REPORT="$RUN/pre-motion-readiness.json"
python3 tools/wait_n04_ready.py --expected-epoch "$N04_EPOCH" \
  --timeout-s 90 --output "$READY_REPORT" > "$RUN/readiness.log" 2>&1 || {
    cat "$READY_REPORT" >&2
    tail -n 120 "$RUN/mapping-stack.log" >&2
    exit 12
  }
if [[ "$MODE" == static ]]; then
  # Let the startup health gate settle before recording a static observation window.
  sleep 12
  python3 tools/wait_n04_ready.py --expected-epoch "$N04_EPOCH" \
    --timeout-s 90 --output "$RUN/post-settle-readiness.json" \
    > "$RUN/post-settle-readiness.log" 2>&1 || {
      cat "$RUN/post-settle-readiness.json" >&2
      tail -n 120 "$RUN/mapping-stack.log" >&2
      exit 12
    }
fi
ros2 param dump --no-daemon --spin-time 1.0 --timeout 10 \
  /drone_0_ego_planner_node > "$RUN/ego-runtime-params.yaml"

DEPTH_TOPIC=$(python3 -c 'import json; print(json.load(open("config/components/mapping/ego_input.json"))["ego_depth_topic"])')
POSE_TOPIC=$(python3 -c 'import json; print(json.load(open("config/components/mapping/ego_input.json"))["ego_pose_topic"])')
RECORDER_SECONDS=40
if [[ "$MODE" == motion_n06 ]]; then
  RECORDER_SECONDS=$(python3 - "$N06_PROFILE" <<'PY'
import json,math,sys
profile=json.load(open(sys.argv[1]))
print(max(40,math.ceil(float(profile.get(
    'record_wall_seconds', float(profile['stop_seconds'])+8)))) )
PY
  )
fi
setsid python3 tools/record_n04_mapping_inputs.py --seconds "$RECORDER_SECONDS" \
  --depth-topic "$DEPTH_TOPIC" --pose-topic "$POSE_TOPIC" \
  --output-dir "$RUN/inputs" > "$RUN/input-recorder.log" 2>&1 &
RECORDER_PID=$!
sleep 1
if [[ "$MODE" == motion || "$MODE" == motion_n06 ]]; then
  if [[ "$MODE" == motion_n06 ]]; then
    setsid python3 tools/run_sensor_motion.py \
      --profile "$N06_PROFILE" \
      --output "$RUN/motion.json" > "$RUN/motion.log" 2>&1 &
  else
    setsid python3 tools/run_sensor_motion.py --output "$RUN/motion.json" \
      > "$RUN/motion.log" 2>&1 &
  fi
  MOTION_PID=$!
fi

capture_snapshot() {
  local index=$1
  python3 tools/capture_live_occupancy_snapshot.py \
    --expected-epoch "$N04_EPOCH" --project-root /workspace \
    --model /workspace/simulation/models/d435i/model.sdf \
    --input-config /workspace/config/components/mapping/ego_input.json \
    --planner-config /workspace/config/components/mapping/ego_planner.json \
    --runtime-params "$RUN/ego-runtime-params.yaml" \
    --source-manifest "$RUN/runtime-contract.json" \
    --min-forwarded-depth-count 40 --max-source-age-s 0.4 \
    --output-dir "$RUN/snapshots/snapshot-$index" \
    > "$RUN/snapshot-$index-capture.log" 2>&1
}

# N06 evaluates a stationary map after the no-control scan. Motion profiles
# finish and clear their wrench before snapshots or the planner-only goal.
if [[ "$MODE" == motion_n06 ]]; then
  wait "$MOTION_PID"
  MOTION_PID=
  sleep 2
fi

# Capture three fresh snapshots under one epoch/map_id. Static mode isolates
# map admission; motion_n06 captures after the observation scan settles.
sleep 6
if [[ "$MODE" == motion || "$MODE" == motion_n06 ]]; then
  [[ -z "$MOTION_PID" ]] || kill -0 "$MOTION_PID" 2>/dev/null || { cat "$RUN/motion.log" >&2; exit 13; }
fi
capture_snapshot 01
sleep 6
if [[ "$MODE" == motion || "$MODE" == motion_n06 ]]; then
  [[ -z "$MOTION_PID" ]] || kill -0 "$MOTION_PID" 2>/dev/null || { cat "$RUN/motion.log" >&2; exit 13; }
fi
capture_snapshot 02
sleep 6
if [[ "$MODE" == motion || "$MODE" == motion_n06 ]]; then
  [[ -z "$MOTION_PID" ]] || kill -0 "$MOTION_PID" 2>/dev/null || { cat "$RUN/motion.log" >&2; exit 13; }
fi
capture_snapshot 03

if [[ -n "$MOTION_PID" ]]; then
  wait "$MOTION_PID"
  MOTION_PID=
fi
wait "$RECORDER_PID"
RECORDER_PID=
sleep 1
if [[ "$MODE" == static || "$MODE" == motion_n06 ]]; then
  PROBE_ARGS=(--run-id "$RUN_ID" --observe-s 2.0
              --output "$RUN/n06-live-layout-probe.json")
  if [[ "$MODE" == motion_n06 ]]; then
    read -r REQUIRE_CERTIFICATE OFFSET_X OFFSET_Y OFFSET_Z HANDOFF_PRESENT HANDOFF_X HANDOFF_Y HANDOFF_Z < <(python3 - "$N06_PROFILE" <<'PY'
import json,sys
profile=json.load(open(sys.argv[1]))
offset=profile.get('planner_goal_offset_xyz_m',[0.5,0.0,0.5])
if len(offset)!=3:
    raise SystemExit('planner_goal_offset_xyz_m must contain exactly three values')
handoff=profile.get('planner_handoff_goal_offset_xyz_m')
if handoff is not None and len(handoff)!=3:
    raise SystemExit('planner_handoff_goal_offset_xyz_m must contain exactly three values')
print('yes' if profile.get('require_snapshot_goal_certificate',False) else 'no',
      *offset, 'yes' if handoff is not None else 'no', *(handoff or [0,0,0]))
PY
    )
    PROBE_ARGS+=(--target-dx-m "$OFFSET_X" --target-dy-m "$OFFSET_Y"
                 --target-dz-m "$OFFSET_Z")
    if [[ "$REQUIRE_CERTIFICATE" == yes ]]; then
      PROBE_ARGS+=(--require-snapshot-certificate)
    fi
    if [[ "$HANDOFF_PRESENT" == yes ]]; then
      PROBE_ARGS+=(--handoff-target-dx-m "$HANDOFF_X"
                   --handoff-target-dy-m "$HANDOFF_Y"
                   --handoff-target-dz-m "$HANDOFF_Z")
    fi
  fi
  python3 tools/probe_n06_live_layout.py "${PROBE_ARGS[@]}" \
    > "$RUN/n06-live-layout-probe.log" 2>&1 || {
      cat "$RUN/n06-live-layout-probe.log" >&2
      exit 16
    }
fi
ros2 node list --no-daemon --spin-time 1.0 > "$RUN/ros-nodes.txt"
ros2 topic list --no-daemon --spin-time 1.0 > "$RUN/ros-topics.txt"
if grep -Ein 'px4|controller|debug_truth|truth_bridge' "$RUN/ros-nodes.txt"; then
  echo 'Unexpected PX4/control/truth node in N04 diagnostic graph' >&2
  exit 14
fi
if grep -En '^/(fmu|debug_truth|truth)(/|$)' "$RUN/ros-topics.txt"; then
  echo 'Unexpected PX4/truth topic in N04 diagnostic graph' >&2
  exit 15
fi

stop_group "$LAUNCH_PID"
LAUNCH_PID=
echo "N04 layout capture complete: $RUN_ID ($LAYOUT_ID, $MODE, epoch $N04_EPOCH)"
