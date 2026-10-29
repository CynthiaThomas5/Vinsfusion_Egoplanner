#!/usr/bin/env bash
# N08-aware, fail-closed mission entry; all PX4 control remains bridge-owned.
set -Ee -o pipefail
cd /workspace
RUN_ID=${1:?run id required}
RUN=/workspace/artifacts/runs/$RUN_ID
PROFILE=${2:-config/components/navigation/room_crossing_goal.json}
COMPLETION_MODE=${3:-single_goal}
TRIAL_KIND=${4:-terminal_stop}
CANCEL_SPEED_MIN=${5:-0.04}
CANCEL_SPEED_MAX=${6:-0.06}
MODE=${D435I_N08_MODE:-execute}
source /opt/ros/jazzy/setup.bash
source /workspace/install/local_setup.bash
export FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/config/middleware/fastdds_local_shm.xml
case "$MODE" in
  hold|compute_only|execute) ;;
  *) echo 'D435I_N08_MODE must be hold, compute_only, or execute' >&2; exit 2 ;;
esac
case "$COMPLETION_MODE" in
  single_goal|round_trip) ;;
  *) echo 'completion mode must be single_goal or round_trip' >&2; exit 2 ;;
esac
case "$TRIAL_KIND" in
  terminal_stop|motion_cancel) ;;
  *) echo 'trial kind must be terminal_stop or motion_cancel' >&2; exit 2 ;;
esac
[[ -f "$RUN/stack-started" ]] || { echo 'Stack did not start' >&2; exit 10; }
[[ ! -e "$RUN/flight.json" && ! -e "$RUN/preflight.json" ]] || { echo 'A task already used this run directory; start a new simulation' >&2; exit 9; }
python3 -c 'import json,sys; from pathlib import Path; sys.path.insert(0,"/workspace/tools"); from flight_profile import legs; rows=legs(json.loads(Path(sys.argv[1]).read_text())); assert len(rows)==1, "N08 mission runner requires exactly one target"' "$PROFILE"
python3 - "$RUN_ID" "$MODE" <<'PY'
import json
from pathlib import Path
import sys

run_id, mode = sys.argv[1:]
record = Path('/workspace/artifacts/runs', run_id + '-stack', 'n08-runtime-mode.json')
data = json.loads(record.read_text()) if record.is_file() else {}
if data.get('mode') != mode:
    raise SystemExit(f'launch mode {data.get("mode")!r} does not match requested mission mode {mode!r}')
if data.get('control_owner') != 'uav_px4_bridge only':
    raise SystemExit('run manifest does not confirm the sole PX4 bridge owner')
if data.get('ground_truth_online_allowed') is not False:
    raise SystemExit('run manifest permits forbidden online truth input')
PY

# User-authorized official EGO navigation uses the generic airborne action path.
# The N08 raw-capsule/braking runner below remains an explicit historical experiment.
POLICY=$(python3 -c 'import json; print(json.load(open("config/components/navigation/task_supervisor.json")).get("collision_policy", "known_free"))')
if [[ "$POLICY" == official_ego ]]; then
  [[ "$MODE" == execute && "$COMPLETION_MODE" == single_goal && "$TRIAL_KIND" == terminal_stop ]] || {
    echo 'Historical N08 hold/compute/cancel/round-trip protocol is not the official navigation entry' >&2; exit 21;
  }
  exec bash tools/n09_runtime.sh "$RUN_ID" "$PROFILE" navigation
fi

# These gates run while PX4 is disarmed and bridge control is disabled.
python3 tools/check_navigation_ready.py "$RUN" > "$RUN/preflight.log" 2>&1
python3 - "$RUN/preflight.json" <<'PY'
import json
import sys
report = json.load(open(sys.argv[1]))
if report.get('passed') is not True:
    raise SystemExit('read-only bridge/localization preflight failed')
PY
python3 tools/check_takeoff_admission.py "$RUN" > "$RUN/takeoff-admission.log"

# Only the bounded terminal-stop protocol may enter native execute mode.
# The runner independently checks build fingerprints, current raw-map capsule,
# original N05 home pad and live freshness before it enables the bridge.
if [[ "$MODE" == execute ]]; then
  [[ "$PROFILE" == config/components/navigation/n08_forward_braking_trial_goal.json ]] || {
    echo 'N08 movement is locked outside the dedicated terminal-stop trial profile' >&2
    exit 20
  }
  python3 - "$PROFILE" "$RUN_ID" <<'PYGATE'
import json,sys
from pathlib import Path
sys.path.insert(0,"/workspace/tools")
from evaluate_n08_curve_certificate import resolve_trial_speed_profile
from n08_trial_gate import trial_limits
profile,run_id=sys.argv[1:]
launch=json.loads(Path('/workspace/artifacts/runs',run_id+'-stack','launch-manifest.json').read_text())
speed=resolve_trial_speed_profile(launch,Path('/workspace'))
limits=trial_limits(json.loads(Path(profile).read_text()),json.loads(Path(speed['path']).read_text()))
if speed['vector_speed_cap_m_s'] != limits['actual_vector_speed_limit_m_s']:
    raise SystemExit('trial profile and launch speed caps differ')
PYGATE
fi

PIDS=()
observe() { local label=$1; shift; "$@" > "$RUN/$label.log" 2>&1 & PIDS+=($!); }
if [[ "$MODE" != hold ]]; then
  observe n08-localization-sources python3 tools/diagnostics/record_n08_localization_sources.py "$RUN"
fi
observe planner python3 tools/diagnostics/record_planner.py "$RUN"
observe alignment python3 tools/diagnostics/record_alignment.py "$RUN"
observe bridge python3 tools/diagnostics/record_bridge.py "$RUN"
observe truth python3 tools/debug_truth/record_truth.py "$RUN"
if [[ "$MODE" == compute_only ]]; then
  observe n08-curve-map python3 tools/diagnostics/capture_n08_curve_map.py "$RUN"
fi

RESULT=0
if [[ "$MODE" == hold ]]; then
  python3 tools/run_vio_no_goal_hover.py --project-root /workspace \
    --goal-config "$PROFILE" --output "$RUN/flight.json" --hover-seconds 30 \
    > "$RUN/flight.log" 2>&1 || RESULT=$?
elif [[ "$MODE" == compute_only ]]; then
  python3 tools/run_n08_compute_only.py --project-root /workspace \
    --goal-config "$PROFILE" --output "$RUN/flight.json" \
    > "$RUN/flight.log" 2>&1 || RESULT=$?
else
  TRIAL_ARGS=(--trial-kind "$TRIAL_KIND")
  if [[ "$TRIAL_KIND" == motion_cancel ]]; then
    TRIAL_ARGS+=(--cancel-speed-window "$CANCEL_SPEED_MIN" "$CANCEL_SPEED_MAX")
  fi
  python3 tools/run_n08_braking_trial.py --project-root /workspace \
    --goal-config "$PROFILE" --output "$RUN/flight.json" \
    --completion-mode "$COMPLETION_MODE" \
    "${TRIAL_ARGS[@]}" \
    > "$RUN/flight.log" 2>&1 || RESULT=$?
fi

if [[ ! -f "$RUN/flight.json" ]]; then
  python3 - "$RUN/flight.json" <<'PY'
import json
from pathlib import Path
import sys
Path(sys.argv[1]).write_text(json.dumps({
    'result': 'FAIL',
    'failure': 'runner exited without writing a terminal record',
    'mission_runtime_mode': 'fail-closed',
}, indent=2) + '\n')
PY
  RESULT=1
fi
for pid in "${PIDS[@]}"; do wait "$pid" || RESULT=1; done
if [[ "$MODE" == compute_only && -f "$RUN/flight.json" ]]; then
  # Preserve the mode-specific cancel/hold/landing diagnosis even if the
  # separate odometry report encounters an unrelated data-availability issue.
  python3 tools/evaluate_n08_compute_only.py "$RUN/flight.json" \
    > "$RUN/n08-compute-only-evaluation.log" || RESULT=$?
  python3 tools/evaluate_n08_curve_certificate.py "$RUN" \
    > "$RUN/n08-curve-certificate.log" || RESULT=$?
fi
if [[ "$RESULT" == 0 || "$MODE" == execute ]]; then
  # A failed return may still contain a complete forward braking interval.
  # Preserve its independent diagnosis while retaining the native FAIL result.
  python3 tools/debug_truth/evaluate_odometry.py "$RUN" > "$RUN/odometry-evaluation.log" || RESULT=$?
  if [[ "$MODE" == execute ]]; then
    python3 tools/debug_truth/evaluate_n08_braking.py "$RUN" --plot \
      --completion-mode "$COMPLETION_MODE" \
      > "$RUN/n08-braking-evaluation.log" || RESULT=$?
  fi
fi
exit "$RESULT"
