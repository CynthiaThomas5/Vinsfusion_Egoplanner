#!/usr/bin/env bash
# Explicit user-invoked flight task; all PX4 control remains owned by the bridge.
set -Ee -o pipefail
cd /workspace
RUN_ID=${1:?run id required}
RUN=/workspace/artifacts/runs/$RUN_ID
source /opt/ros/jazzy/setup.bash
source /workspace/install/local_setup.bash
export FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/config/middleware/fastdds_local_shm.xml
for ((i=0;i<100;i++)); do [[ ! -f "$RUN/stack-started" ]] || break; sleep 1; done
[[ -f "$RUN/stack-started" ]] || { echo 'Stack did not start' >&2; exit 10; }
[[ ! -e "$RUN/flight.json" && ! -e "$RUN/preflight.json" ]] || { echo 'A task already used this run directory; start a new simulation' >&2; exit 9; }
PIDS=()
observe() { local label=$1; shift; "$@" > "$RUN/$label.log" 2>&1 & PIDS+=("$!"); }
observe planner python3 tools/diagnostics/record_planner.py "$RUN"
observe alignment python3 tools/diagnostics/record_alignment.py "$RUN"
observe bridge python3 tools/diagnostics/record_bridge.py "$RUN"
observe truth python3 tools/debug_truth/record_truth.py "$RUN"
python3 tools/run_vio_ego_flight.py --project-root /workspace --output "$RUN/flight.json" > "$RUN/flight.log" 2>&1 &
FLIGHT=$!
for ((i=0;i<30;i++)); do [[ ! -f "$RUN/flight-probe-ready" ]] || break; sleep 1; done
[[ -f "$RUN/flight-probe-ready" ]]
python3 tools/check_navigation_ready.py "$RUN" > "$RUN/preflight.log" 2>&1
RESULT=0
wait "$FLIGHT" || RESULT=$?
for pid in "${PIDS[@]}"; do wait "$pid" || RESULT=1; done
if [[ "$RESULT" == 0 ]]; then
  python3 tools/debug_truth/evaluate_arrival.py "$RUN" > "$RUN/arrival-evaluation.log"
  python3 tools/debug_truth/evaluate_clearance.py "$RUN" > "$RUN/crossing-evaluation.log"
  python3 tools/check_navigation_result.py "$RUN"
fi
exit "$RESULT"
