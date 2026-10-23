#!/usr/bin/env bash
# Explicit observation only; corrected poses are never remapped into localization.
set -Ee -o pipefail
cd /workspace
source /opt/ros/jazzy/setup.bash
source /workspace/install/local_setup.bash
export FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/config/middleware/fastdds_local_shm.xml
RUN_ID=${1:?run id required}
[[ "$RUN_ID" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$ ]] || exit 2
for ((i=0;i<100;i++)); do [[ ! -f "artifacts/runs/$RUN_ID/stack-started" ]] || break; sleep 1; done
[[ -f "artifacts/runs/$RUN_ID/stack-started" ]] || { echo 'Stack did not start' >&2; exit 10; }
RESULT=0
python3 tools/run_loop_observer.py "$RUN_ID" --config "${2:-config/components/localization/loop_observer.json}" || RESULT=$?
printf '%s\n' "$RESULT" > "artifacts/runs/$RUN_ID/loop-backend-exit-code"
exit "$RESULT"
