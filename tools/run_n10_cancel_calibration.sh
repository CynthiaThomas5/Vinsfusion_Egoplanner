#!/usr/bin/env bash
# N10 diagnostic: cancel one official EGO goal at a measured PX4 speed.
set -Ee -o pipefail
cd /workspace
RUN_ID=${1:?run id required}
PROFILE=${2:?goal profile required}
SPEED_MIN=${3:?cancel speed minimum required}
SPEED_MAX=${4:?cancel speed maximum required}
RUN=/workspace/artifacts/runs/$RUN_ID
MODE=${D435I_N08_MODE:-execute}
source /opt/ros/jazzy/setup.bash
source /workspace/install/local_setup.bash
export FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/config/middleware/fastdds_local_shm.xml

[[ -f "$RUN/stack-started" ]] || { echo 'Stack did not start' >&2; exit 10; }
[[ "$MODE" == execute ]] || { echo 'N10 cancellation measurement requires PX4 execute mode' >&2; exit 11; }
[[ -f "$RUN/n09-contact-model-manifest.json" ]] || { echo 'Read-only contact overlay missing' >&2; exit 12; }
[[ ! -e "$RUN/flight.json" && ! -e "$RUN/preflight.json" ]] || {
  echo 'A task already used this run directory; start a new simulation' >&2; exit 9;
}
python3 - "$PROFILE" "$SPEED_MIN" "$SPEED_MAX" <<'PY'
import math
import sys
from pathlib import Path
sys.path.insert(0, '/workspace/tools')
from flight_profile import legs
root=Path('/workspace')
profile=Path(sys.argv[1])
if profile.is_absolute() or not profile.resolve().is_relative_to(root):
    raise SystemExit('Goal profile must be project-relative')
if len(legs(__import__('json').loads(profile.read_text()))) != 1:
    raise SystemExit('N10 cancellation diagnostic requires exactly one EGO goal')
lower,upper=map(float,sys.argv[2:])
if not (math.isfinite(lower) and math.isfinite(upper) and 0.0 < lower < upper):
    raise SystemExit('Invalid PX4 horizontal speed trigger window')
PY

python3 tools/runtime_manifest.py "$RUN/n09-runtime-contract-current.json"
python3 - "$RUN" "$RUN_ID" "$PROFILE" "$SPEED_MIN" "$SPEED_MAX" <<'PY'
import hashlib
import json
import sys
from pathlib import Path
run=Path(sys.argv[1]);run_id,profile,lower,upper=sys.argv[2:]
runtime=json.loads((run/'runtime-contract.json').read_text())
current=json.loads((run/'n09-runtime-contract-current.json').read_text())
launch=json.loads(Path('/workspace/artifacts/runs',run_id+'-stack','launch-manifest.json').read_text())
contact=json.loads((run/'n09-contact-model-manifest.json').read_text())
world=json.loads((run/'world.json').read_text())
if runtime.get('sha256') != current.get('sha256'):
    raise SystemExit('Runtime source/configuration changed after SITL startup')
params=launch.get('ego_launch_arguments',{})
if (params.get('max_vel') != 0.8 or params.get('max_acc') != 0.25
        or params.get('planning_horizon') != 5.0
        or params.get('official_ego_collision_policy') is not True):
    raise SystemExit('Loaded EGO planner profile does not match the N10.3 frozen profile')
if not contact.get('read_only_observation_only') or contact.get('collision_geometry_changed'):
    raise SystemExit('Contact overlay is not read-only or changed collision geometry')
if 'gz::sim::systems::Contact' not in world.get('world_plugins',[]):
    raise SystemExit('Gazebo Contact plugin is not loaded')
(run/'n10-cancel-run-manifest.json').write_text(json.dumps({
    'schema':'n10-cancel-run-manifest/v1','run_id':run_id,
    'goal_profile':profile,'goal_profile_sha256':hashlib.sha256(Path('/workspace',profile).read_bytes()).hexdigest(),
    'cancel_speed_window_px4_horizontal_m_s':[float(lower),float(upper)],
    'runtime_contract_sha256':runtime['sha256'],
    'localization_quality_freshness_gates':'removed',
    'localization_policy_sha256':hashlib.sha256(Path('/workspace/config/components/localization/health.json').read_bytes()).hexdigest(),
    'collision_policy':'official_ego','loaded_ego_parameters':params,
    'contact_model_read_only':True,
    'contact_model_sha256':hashlib.sha256((run/'n09-contact-model-manifest.json').read_bytes()).hexdigest(),
    'ground_truth_online_allowed':False,'px4_control_owner':'uav_px4_bridge only',
},indent=2)+'\n')
PY

python3 tools/check_navigation_ready.py "$RUN" > "$RUN/preflight.log" 2>&1
python3 - "$RUN/preflight.json" <<'PY'
import json,sys
if json.load(open(sys.argv[1])).get('passed') is not True:
    raise SystemExit('Read-only navigation/PX4 preflight failed')
PY
python3 tools/check_takeoff_admission.py "$RUN" > "$RUN/takeoff-admission.log"
ros2 topic info /move_base_simple/goal --verbose > "$RUN/legacy-simple-goal-graph.txt" 2>&1 || true
if grep -Eq 'Subscription count: [1-9]' "$RUN/legacy-simple-goal-graph.txt"; then
  echo 'Legacy goal subscriber detected; no flight started' >&2; exit 13
fi
EGO_GRAPH_READY=0
for _ in $(seq 1 20); do
  if ros2 topic info /navigation/ego_goal --verbose > "$RUN/validated-ego-goal-graph.txt" 2>&1 \
      && grep -Fxq 'Publisher count: 1' "$RUN/validated-ego-goal-graph.txt" \
      && grep -Fxq 'Subscription count: 2' "$RUN/validated-ego-goal-graph.txt" \
      && grep -Fq 'Node name: uav_navigation' "$RUN/validated-ego-goal-graph.txt" \
      && grep -Fq 'Node name: drone_0_ego_planner_node' "$RUN/validated-ego-goal-graph.txt" \
      && grep -Fq 'Node name: uav_px4_bridge' "$RUN/validated-ego-goal-graph.txt"; then
    EGO_GRAPH_READY=1
    break
  fi
  sleep 0.5
done
[[ "$EGO_GRAPH_READY" == 1 ]] || { echo 'EGO goal graph is missing the expected planner and bridge subscribers' >&2; exit 14; }

PIDS=()
observe() { local label=$1; shift; "$@" > "$RUN/$label.log" 2>&1 & PIDS+=($!); }
stop_observers() {
  local pid
  for pid in "${PIDS[@]}"; do kill -INT "$pid" 2>/dev/null || true; done
  for pid in "${PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done
  PIDS=()
}
trap stop_observers EXIT INT TERM
observe truth python3 tools/debug_truth/record_truth.py "$RUN"
observe alignment python3 tools/diagnostics/record_alignment.py "$RUN"
observe planner python3 tools/diagnostics/record_planner.py "$RUN"
observe bridge python3 tools/diagnostics/record_bridge.py "$RUN"
observe contacts python3 tools/record_n09_contacts.py "$RUN"
observe source-timeline python3 tools/diagnostics/record_n08_localization_sources.py \
  "$RUN" --duration-wall-s 1500
for _ in $(seq 1 200); do
  [[ ! -f "$RUN/n09-contact-observer-ready.json" ]] || break
  sleep 0.1
done
python3 - "$RUN/n09-contact-observer-ready.json" <<'PY'
import json,sys
from pathlib import Path
path=Path(sys.argv[1])
if not path.is_file() or json.loads(path.read_text()).get('ready') is not True:
    raise SystemExit('Contact sensors are not ready; flight refused')
PY

sleep 2

FLIGHT_EXIT=0
python3 tools/run_vio_ego_flight.py --project-root /workspace \
  --goal-config "$PROFILE" --output "$RUN/flight.json" \
  --precondition-timeout-s 30 --flight-timeout-s 360 \
  --landing-timeout-s 45 \
  --cancel-speed-window "$SPEED_MIN" "$SPEED_MAX" \
  > "$RUN/flight.log" 2>&1 || FLIGHT_EXIT=$?
if [[ ! -f "$RUN/flight.json" ]]; then
  echo 'Flight runner did not write its terminal record; keep this project container running' >&2
  exit 15
fi

sleep 2
stop_observers
trap - EXIT INT TERM
OBSERVER_EXIT=0
python3 - "$RUN" <<'PY' || OBSERVER_EXIT=1
import json,sys
from pathlib import Path
run=Path(sys.argv[1])
for name in ('debug-truth-evaluation.json','alignment-observation.json',
             'planner-observation.json','bridge-observation.json',
             'n09-contact-observation.json'):
    path=run/name
    if not path.is_file():
        print('missing observer output:',name); raise SystemExit(1)
    data=json.loads(path.read_text())
    if data.get('terminal_flight_record_observed') is not True:
        print('observer did not reach flight terminal:',name,
              data.get('observation_stop_reason')); raise SystemExit(1)
PY

python3 tools/probe_px4_bridge_live.py --seconds 6 \
  --output "$RUN/postflight-px4-bridge-readback.json" \
  > "$RUN/postflight-readback.log" 2>&1
python3 - "$RUN/postflight-px4-bridge-readback.json" "$RUN/safe-to-stop.json" <<'PY'
import json,sys
from pathlib import Path
report=json.loads(Path(sys.argv[1]).read_text())
bridge=report.get('latest',{}).get('bridge',{})
safe=(bridge.get('phase')=='LANDED' and bridge.get('landed') is True
      and bridge.get('armed') is False and bridge.get('control_enabled') is False
      and report.get('vehicle_remained_disarmed') is True
      and report.get('control_samples_zero') is True)
Path(sys.argv[2]).write_text(json.dumps({
 'safe_to_stop_project_container':safe,'bridge':bridge,
 'vehicle_remained_disarmed':report.get('vehicle_remained_disarmed'),
 'control_samples_zero':report.get('control_samples_zero')},indent=2)+'\n')
if not safe:
    raise SystemExit('Independent terminal readback unsafe/incomplete; leave container running')
PY

RESULT=$FLIGHT_EXIT
[[ "$OBSERVER_EXIT" == 0 ]] || RESULT=1
if python3 - "$RUN/flight.json" <<'PY'
import json,sys
raise SystemExit(0 if json.load(open(sys.argv[1])).get('action_goal_sent') else 1)
PY
then
  python3 - "$RUN" <<'PY' || RESULT=1
import json,sys
from pathlib import Path
sys.path.insert(0,'/workspace/tools')
from n09_contact_evaluation import evaluate_contacts
run=Path(sys.argv[1]);flight=json.loads((run/'flight.json').read_text())
report=evaluate_contacts(json.loads((run/'n09-contact-observation.json').read_text()),
 json.loads((run/'n09-contact-model-manifest.json').read_text()),
 [json.loads(x) for x in (run/'bridge-alignment-timeline.jsonl').read_text().splitlines() if x.strip()],
 int(flight['goal']['source_ns']))
(run/'vehicle-contact-evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
if not report.get('passed'): raise SystemExit('Contact evaluation failed')
PY
  python3 tools/debug_truth/evaluate_odometry.py "$RUN" \
    > "$RUN/odometry-evaluation.log" 2>&1 || RESULT=1
  python3 tools/debug_truth/evaluate_n10_cancel_braking.py "$RUN" \
    > "$RUN/n10-cancel-braking-evaluation.log" 2>&1 || RESULT=1
else
  RESULT=1
fi
exit "$RESULT"
