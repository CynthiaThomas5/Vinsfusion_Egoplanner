#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
RUN_ID=${1:?Usage: run_n05_preflight_layout.sh RUN_ID wall_box_column|corridor_box_column}
LAYOUT=${2:?Specify wall_box_column or corridor_box_column}
[[ "$RUN_ID" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$ ]] || { echo 'Invalid run id' >&2; exit 2; }
[[ "$LAYOUT" == wall_box_column || "$LAYOUT" == corridor_box_column ]] || { echo 'Invalid N05 layout' >&2; exit 2; }
RUN_DIR="$ROOT/artifacts/runs/$RUN_ID"
CONTAINER="d435i-$RUN_ID"
[[ ! -e "$RUN_DIR" ]] || { echo "Refusing to overwrite $RUN_DIR" >&2; exit 9; }

run_in_container() {
  docker exec "$CONTAINER" bash -c \
    'set +u; source /opt/ros/jazzy/setup.bash; source /workspace/install/local_setup.bash; set -u; exec "$@"' \
    n05-runner "$@"
}

cleanup() {
  local code=$?
  trap - EXIT INT TERM
  if docker inspect "$CONTAINER" >/dev/null 2>&1; then
    if [[ -n "$(docker ps -q --filter "name=^/${CONTAINER}$")" ]]; then
      if [[ -f "$RUN_DIR/n05-fixture.log" && ! -f "$RUN_DIR/fixture-result.json" ]]; then
        docker exec "$CONTAINER" touch "/workspace/artifacts/runs/$RUN_ID/n05-release-fixture" >/dev/null 2>&1 || true
        for ((i=0; i<660; ++i)); do
          [[ -f "$RUN_DIR/fixture-result.json" ]] && break
          [[ -z "$(docker ps -q --filter "name=^/${CONTAINER}$")" ]] && break
          sleep 1
        done
      fi
      if [[ -f "$RUN_DIR/fixture-result.json" ]]; then
        local unsafe
        unsafe=$(python3 - "$RUN_DIR/fixture-result.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print(bool(d.get('fixture_may_remain_attached')
           or (d.get('fixture_spawned') and not d.get('fixture_removed'))))
PY
        )
        if [[ "$unsafe" == True ]]; then
          echo "Fixture state was not confirmed detached; keeping $CONTAINER running for monitoring" >&2
          echo 'Do not stop this project container until the N05 fixture state is resolved.' \
            > "$RUN_DIR/n05-monitor-required.txt"
          exit "$code"
        fi
      fi
      docker stop -t 15 "$CONTAINER" >/dev/null 2>&1 || true
    fi
  fi
  exit "$code"
}
trap cleanup EXIT INT TERM

bash tools/project.sh sim "$RUN_ID" >/dev/null
mkdir -p "$RUN_DIR"
for ((i=0; i<240; ++i)); do
  [[ -f "$RUN_DIR/stack-started" ]] && break
  if [[ -z "$(docker ps -q --filter "name=^/${CONTAINER}$")" ]]; then
    docker logs "$CONTAINER" > "$RUN_DIR/container-startup.log" 2>&1 || true
    echo "SITL container exited before stack readiness: $RUN_ID" >&2
    exit 10
  fi
  sleep 1
done
[[ -f "$RUN_DIR/stack-started" ]] || { echo 'Timed out waiting for current VINS/EGO stack' >&2; exit 11; }

python3 - "$RUN_DIR/n05-run-inputs.json" "$RUN_ID" "$LAYOUT" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path.cwd()
files=[
 'tools/probe_preflight_scan.py','tools/check_n05_entry_live.py','tools/n05_entry.py',
 'tools/evaluate_n05_entry.py','tools/summarize_n05_layout_run.py',
 'config/components/navigation/vehicle_envelope.json',
 'config/components/mapping/ego_planner.json',
 'config/components/simulation/n04_geometry_layouts.json',
 'config/components/simulation/preflight_scan.json',
 'simulation/models/preflight_scan_fixture/model.sdf',
 'simulation/models/x500_d435i/model.sdf','simulation/models/d435i/model.sdf',
 'external/PX4-Autopilot/Tools/simulation/gz/models/x500_base/model.sdf',
]
hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}
run_id,layout=sys.argv[2:]
Path(sys.argv[1]).write_text(json.dumps({
 'schema':'n05-run-inputs/v1','run_id':run_id,'layout_id':layout,
 'container_image':json.load(open('config/runtime.json'))['image_id'],
 'world_scene':'current PX4 SITL scene plus selected N04 geometry, shifted +1.5 m along spawn yaw',
 'control_scope':'DISARMED whole-airframe support scan and read-only occupancy check',
 'file_sha256':hashes},indent=2)+'\n')
PY

echo "Capturing initial online map view for $RUN_ID ($LAYOUT)"
run_in_container python3 tools/check_n05_entry_live.py \
  --output-dir "/workspace/artifacts/runs/$RUN_ID/n05-before" --wait-s 150
run_in_container python3 tools/evaluate_n05_entry.py \
  --live-report "/workspace/artifacts/runs/$RUN_ID/n05-before/n05-live-entry-check.json"

docker exec -d "$CONTAINER" bash -c '
  set +u
  source /opt/ros/jazzy/setup.bash
  source /workspace/install/local_setup.bash
  set -u
  run_id=$1; layout=$2; run="/workspace/artifacts/runs/$1"
  if python3 /workspace/tools/probe_preflight_scan.py --run "$run" --profile coverage \
       --n05-layout "$layout" --hold-for-live-check > "$run/n05-fixture.log" 2>&1; then
    code=0
  else
    code=$?
  fi
  printf "%s\n" "$code" > "$run/n05-fixture.exitcode"
  exit "$code"
' n05-probe "$RUN_ID" "$LAYOUT"

ready=0
for ((i=0; i<1800; ++i)); do
  if [[ -f "$RUN_DIR/n05-prescan-ready.json" ]]; then ready=1; break; fi
  if [[ -f "$RUN_DIR/n05-fixture.exitcode" ]]; then
    cat "$RUN_DIR/n05-fixture.log" >&2
    echo 'Unarmed support scan ended before its online-check window' >&2
    exit 12
  fi
  if [[ -z "$(docker ps -q --filter "name=^/${CONTAINER}$")" ]]; then
    echo 'SITL container exited during the support scan' >&2
    exit 13
  fi
  sleep 1
done
[[ "$ready" == 1 ]] || { echo 'Timed out waiting for support scan completion' >&2; exit 14; }

python3 - "$RUN_DIR/n05-prescan-ready.json" "$LAYOUT" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
if d.get('layout_id')!=sys.argv[2] or d.get('attachment')!='attached':
 raise SystemExit('support-scan ready marker does not match the selected layout/attachment')
if d.get('truth_input_used') or d.get('control_or_goal_published'):
 raise SystemExit('support-scan scope violation')
print('support scan reached return pose:',d['epoch'],d['map_id'])
PY

run_in_container python3 tools/check_n05_entry_live.py \
  --output-dir "/workspace/artifacts/runs/$RUN_ID/n05-after" --wait-s 120
run_in_container python3 tools/evaluate_n05_entry.py \
  --live-report "/workspace/artifacts/runs/$RUN_ID/n05-after/n05-live-entry-check.json"
run_in_container touch "/workspace/artifacts/runs/$RUN_ID/n05-release-fixture"

for ((i=0; i<180; ++i)); do
  [[ -f "$RUN_DIR/n05-fixture.exitcode" ]] && break
  sleep 1
done
[[ -f "$RUN_DIR/n05-fixture.exitcode" ]] || { echo 'Support scan did not detach/close within 180 s' >&2; exit 15; }
SCAN_EXIT_CODE=$(cat "$RUN_DIR/n05-fixture.exitcode")
if [[ "$SCAN_EXIT_CODE" != 0 ]]; then
  python3 - "$RUN_DIR/fixture-result.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
if (d.get('completed_stages') != 12 or not d.get('n05_live_check_completed')
        or 'detached' not in d.get('attachment_states', [])
        or not d.get('fixture_removed') or d.get('fixture_may_remain_attached')):
 raise SystemExit('scan process failed before a complete, detached observation; refusing post-release continuation')
print('scan completed and fixture absent; preserving post-release status:',d.get('error',''))
PY
  echo "Support scan reported a post-release health/status error (exit $SCAN_EXIT_CODE); running explicit post-release admission check."
fi

if run_in_container python3 tools/check_n05_entry_live.py \
     --output-dir "/workspace/artifacts/runs/$RUN_ID/n05-post-release" --wait-s 120 \
     > "$RUN_DIR/n05-post-release-check.log" 2>&1; then
  cat "$RUN_DIR/n05-post-release-check.log"
  run_in_container python3 tools/evaluate_n05_entry.py \
    --live-report "/workspace/artifacts/runs/$RUN_ID/n05-post-release/n05-live-entry-check.json"
else
  cat "$RUN_DIR/n05-post-release-check.log" >&2
  [[ -f "$RUN_DIR/n05-post-release/n05-live-entry-check-error.json" ]] || {
    echo 'Post-release checker failed without a structured refusal record' >&2
    exit 17
  }
  echo 'Post-release entry remained fail-closed; structured prerequisite failure saved.'
fi

run_in_container python3 tools/summarize_n05_layout_run.py \
  --run-dir "/workspace/artifacts/runs/$RUN_ID"

echo "N05 unarmed layout diagnostic complete: $RUN_ID ($LAYOUT)"
