#!/usr/bin/env bash
# Fresh-gated N09 VIO/EGO waypoint mission; PX4 output remains bridge-owned.
set -Ee -o pipefail
cd /workspace
RUN_ID=${1:?run id required}
PROFILE=${2:-config/components/navigation/n09_3d_waypoint_goal.json}
RUN=/workspace/artifacts/runs/$RUN_ID
MODE=${D435I_N08_MODE:-execute}
PURPOSE=${3:-n09}
source /opt/ros/jazzy/setup.bash
source /workspace/install/local_setup.bash
export FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/config/middleware/fastdds_local_shm.xml

[[ -f "$RUN/stack-started" ]] || { echo 'Stack did not start' >&2; exit 10; }
[[ "$MODE" == execute ]] || { echo 'N09 requires the bridge execute input; compute-only is a separate no-flight diagnostic' >&2; exit 11; }
[[ -f "$RUN/n09-contact-model-manifest.json" ]] || {
  echo 'N09 requires its read-only contact-instrumented model overlay; restart with D435I_N09_CONTACTS=1' >&2
  exit 13
}
[[ ! -e "$RUN/flight.json" && ! -e "$RUN/preflight.json" ]] || {
  echo 'A task already used this run directory; start a new simulation' >&2; exit 9;
}
python3 - "$PROFILE" <<'PY'
import json
import sys
from pathlib import Path
sys.path.insert(0, '/workspace/tools')
from flight_profile import legs
profile = Path(sys.argv[1])
if profile.is_absolute() or not profile.resolve().is_relative_to(Path('/workspace')):
    raise SystemExit('N09 goal profile must be project-relative')
rows = legs(json.loads(profile.read_text()))
if len(rows)<2 or json.loads(profile.read_text()).get('continuous_navigation_min_sim_s')!=300:
    raise SystemExit('Continuous qualification requires the bounded >=300sim multi-goal profile')
PY

python3 tools/runtime_manifest.py "$RUN/n09-runtime-contract-current.json"
python3 - "$RUN" "$RUN_ID" "$PROFILE" "$MODE" <<'PY'
import hashlib
import json
import sys
from pathlib import Path
run, run_id, profile_path, mode = sys.argv[1:]
run = Path(run)
stack = Path('/workspace/artifacts/runs', run_id + '-stack')
mode_record = json.loads((stack / 'n08-runtime-mode.json').read_text())
launch = json.loads((stack / 'launch-manifest.json').read_text())
runtime = json.loads((run / 'runtime-contract.json').read_text())
current = json.loads((run / 'n09-runtime-contract-current.json').read_text())
contact_model = json.loads((run / 'n09-contact-model-manifest.json').read_text())
world = json.loads((run / 'world.json').read_text())
if mode_record.get('mode') != mode or mode_record.get('control_owner') != 'uav_px4_bridge only':
    raise SystemExit('launch mode or unique PX4 bridge control owner mismatch')
if mode_record.get('ground_truth_online_allowed') is not False:
    raise SystemExit('online ground truth is forbidden for N09 control')
if runtime.get('sha256') != current.get('sha256'):
    raise SystemExit('runtime sources/config/install changed after simulation startup')
if not contact_model.get('read_only_observation_only') or contact_model.get('collision_geometry_changed'):
    raise SystemExit('N09 contact overlay is not read-only or changed collision geometry')
if 'gz::sim::systems::Contact' not in world.get('world_plugins', []):
    raise SystemExit('Gazebo Contact system is not loaded in the active world')
profile_hash = hashlib.sha256(Path('/workspace', profile_path).read_bytes()).hexdigest()
capture_config = Path('/workspace/config/n10_capture.json')
n10_capture = json.loads(
    (run / 'n10-capture-launch-manifest.json').read_text()).get('n10_capture', {}) \
    if (run / 'n10-capture-launch-manifest.json').is_file() else {}
if not n10_capture:
    n10_capture = {
        'enabled': False,
        'capture_config': 'config/n10_capture.json',
        'capture_config_sha256': hashlib.sha256(capture_config.read_bytes()).hexdigest(),
        'runtime_effect': False,
    }
n10_capture['capture_launch_manifest_sha256'] = (
    hashlib.sha256((run / 'n10-capture-launch-manifest.json').read_bytes()).hexdigest()
    if (run / 'n10-capture-launch-manifest.json').is_file() else None)
(run / 'n09-run-manifest.json').write_text(json.dumps({
    'schema': 'n09-run-manifest/v1', 'run_id': run_id,
    'goal_profile': profile_path, 'goal_profile_sha256': profile_hash,
    'runtime_contract_sha256': runtime['sha256'],
    'contact_model_sha256': hashlib.sha256(
        (run / 'n09-contact-model-manifest.json').read_bytes()).hexdigest(),
    'contact_world_sha256': hashlib.sha256((run / 'vio_initialization.sdf').read_bytes()).hexdigest(),
    'launch_manifest': launch,
    'bridge_input_topic': mode_record.get('bridge_trajectory_input_topic'),
    'control_owner': mode_record.get('control_owner'),
    'ground_truth_online_allowed': mode_record.get('ground_truth_online_allowed'),
    'n10_capture': n10_capture,
}, indent=2) + '\n')
PY

PIDS=()
observe() { local label=$1; shift; "$@" > "$RUN/$label.log" 2>&1 & PIDS+=("$!"); }
stop_observers() {
  local pid
  for pid in "${PIDS[@]}"; do kill -INT "$pid" 2>/dev/null || true; done
  for pid in "${PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done
  PIDS=()
}
trap stop_observers EXIT
observe truth python3 tools/debug_truth/record_truth.py "$RUN"
observe alignment python3 tools/diagnostics/record_alignment.py "$RUN"
observe planner python3 tools/diagnostics/record_planner.py "$RUN"
observe bridge python3 tools/diagnostics/record_bridge.py "$RUN"
observe contacts python3 tools/record_n09_contacts.py "$RUN"
SOURCE_TIMELINE_WALL_S=$(python3 - "$PROFILE" <<'PY'
import json
import sys
from pathlib import Path
profile = json.loads(Path(sys.argv[1]).read_text())
print(float(profile.get('source_timeline_wall_s', 600.0)))
PY
)
observe source-timeline python3 tools/diagnostics/record_n08_localization_sources.py \
  "$RUN" --duration-wall-s "$SOURCE_TIMELINE_WALL_S"


# Independent vertical takeoff uses the canonical policy; EGO stays idle until airborne.
python3 tools/check_navigation_ready.py "$RUN" > "$RUN/preflight.log" 2>&1
python3 - "$RUN/preflight.json" <<'PY'
import json
import sys
if json.load(open(sys.argv[1])).get('passed') is not True:
    raise SystemExit('N09 read-only bridge/localization preflight failed')
PY
python3 tools/check_takeoff_admission.py "$RUN" > "$RUN/takeoff-admission.log"

# The former fixed-height manual waypoint must have no active EGO subscriber.
ros2 topic info /move_base_simple/goal --verbose > "$RUN/legacy-simple-goal-graph.txt" 2>&1 || true
if grep -Eq 'Subscription count: [1-9]' "$RUN/legacy-simple-goal-graph.txt"; then
  echo 'Unsafe legacy /move_base_simple/goal subscriber is still active' >&2
  exit 12
fi
EGO_GRAPH_READY=0
for _ in $(seq 1 20); do
  if ros2 topic info /navigation/ego_goal --verbose \
      > "$RUN/validated-ego-goal-graph.txt" 2>&1 \
      && python3 tools/check_ego_goal_graph.py "$RUN/validated-ego-goal-graph.txt"; then
    EGO_GRAPH_READY=1
    break
  fi
  sleep 0.5
done
if [[ "$EGO_GRAPH_READY" != 1 ]]; then
  echo 'EGO navigation graph did not become ready with one supervisor publisher and the planner/bridge subscribers' >&2
  cat "$RUN/validated-ego-goal-graph.txt" >&2
  exit 14
fi


for _ in $(seq 1 200); do
  [[ ! -f "$RUN/n09-contact-observer-ready.json" ]] || break
  sleep 0.1
done
python3 - "$RUN/n09-contact-observer-ready.json" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.is_file() or json.loads(path.read_text()).get('ready') is not True:
    raise SystemExit('N09 contact sensors are not all advertised; flight refused')
PY

RESULT=0
python3 tools/run_vio_ego_flight.py --project-root /workspace \
  --goal-config "$PROFILE" --output "$RUN/flight.json" \
  --flight-timeout-s 360 --landing-timeout-s 60 \
  > "$RUN/flight.log" 2>&1 || RESULT=$?

# Postflight evidence only: no new launch or in-flight decision branch.
if [[ -f "$RUN/flight.json" ]] && python3 - "$RUN/flight.json" <<'PYIDENTITY'
import json,sys
f=json.load(open(sys.argv[1]));raise SystemExit(0 if f.get('goal_id') and f.get('localization_epoch') else 1)
PYIDENTITY
then
  read -r GOAL_ID EPOCH < <(python3 -c 'import json,sys; f=json.load(open(sys.argv[1])); print(f["goal_id"],f["localization_epoch"])' "$RUN/flight.json")
  python3 tools/probe_px4_bridge_live.py --seconds 15 --direct-sim-time \
    --expected-goal-id "$GOAL_ID" --expected-epoch "$EPOCH" \
    --output "$RUN/postflight-px4-bridge-readback.json" > "$RUN/postflight-readback.log" 2>&1 || RESULT=1
  python3 tools/write_navigation_terminal.py "$RUN" > "$RUN/terminal-evidence.log" 2>&1 || RESULT=1
fi

# After the independent flight/landing, verify terminal refusal while disarmed.
if [[ -f "$RUN/flight.json" ]]; then
  python3 tools/run_n09_live_refusal.py "$RUN/n09-live-refusal.json" \
    > "$RUN/n09-live-refusal.log" || RESULT=1
fi

for pid in "${PIDS[@]}"; do
  wait "$pid" || RESULT=1
done
PIDS=()

CAPTURE_ENABLED=$(python3 - "$RUN/n09-run-manifest.json" <<'PY'
import json,sys
from pathlib import Path
path=Path(sys.argv[1])
record=json.loads(path.read_text()) if path.is_file() else {}
print(int((record.get('n10_capture') or {}).get('enabled') is True))
PY
) || CAPTURE_ENABLED=0
if [[ "$CAPTURE_ENABLED" == 1 ]]; then
  for _ in $(seq 1 400); do
    [[ ! -f "$RUN/n10-sensor-capture.json" || ! -f "$RUN/n10-resource-observation.json" ]] || break
    sleep 0.1
  done
fi
if [[ "$CAPTURE_ENABLED" == 1 && -f "$RUN/n10-sensor-capture.json" ]]; then
  # Offline evidence status cannot change the mission result or flight behavior.
  python3 tools/debug_truth/evaluate_n10_sensor_capture.py "$RUN" \
    > "$RUN/n10-sensor-capture-evaluation.log" \
    || echo 'N10 sensor capture evaluation is INSUFFICIENT; task already ended' >&2
fi

if [[ -f "$RUN/flight.json" ]] && python3 - "$RUN/flight.json" <<'PY'
import json
import sys
raise SystemExit(0 if json.load(open(sys.argv[1])).get('action_goal_sent') else 1)
PY
then
  python3 tools/debug_truth/evaluate_arrival.py "$RUN" \
    > "$RUN/arrival-evaluation.log" || RESULT=1
  python3 - "$RUN" <<'PYCONTACT' || RESULT=1
import json
from pathlib import Path
import sys
sys.path.insert(0, '/workspace/tools')
from n09_contact_evaluation import evaluate_contacts
run=Path(sys.argv[1])
flight=json.loads((run/'flight.json').read_text())
report=evaluate_contacts(
    json.loads((run/'n09-contact-observation.json').read_text()),
    json.loads((run/'n09-contact-model-manifest.json').read_text()),
    [json.loads(line) for line in (run/'bridge-alignment-timeline.jsonl').read_text().splitlines() if line.strip()],
    int(flight['goal']['source_ns']))
(run/'vehicle-contact-evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
if not report['passed']: raise SystemExit('prohibited or unobserved vehicle contact')
PYCONTACT
  if [[ "$PURPOSE" == n09 ]]; then
    python3 tools/evaluate_n09_mission.py "$RUN" \
      > "$RUN/n09-mission-evaluation.log" || RESULT=1
  else
    python3 tools/debug_truth/evaluate_navigation_mission.py "$RUN" > "$RUN/mission-evaluation.log" || RESULT=1
  fi
else
  RESULT=1
fi
exit "$RESULT"
