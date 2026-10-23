#!/usr/bin/env bash
# Host entry point. No build or runtime input is taken from historical runs.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
ACTION=${1:-help}
[[ $# -eq 0 ]] || shift
read_config() { python3 -c 'import json,sys; print(json.load(open("config/runtime.json"))[sys.argv[1]])' "$1"; }
IMAGE=$(read_config image)
EXPECTED=$(read_config image_id)
require_image() {
  [[ "$(docker image inspect "$IMAGE" --format '{{.Id}}')" == "$EXPECTED" ]] || {
    echo 'Fixed container image is missing or mismatched; see docker/README.md' >&2; exit 10;
  }
}
case "$ACTION" in
  fetch) exec python3 tools/fetch_dependencies.py "$@" ;;
  build) require_image; exec docker run --rm -v "$ROOT:/workspace:rw" -w /workspace "$IMAGE" bash tools/build_runtime.sh "$@" ;;
  test) require_image; exec docker run --rm -v "$ROOT:/workspace:rw" -w /workspace "$IMAGE" bash -c 'source /opt/ros/jazzy/setup.bash; source install/local_setup.bash; python3 -m unittest discover -s tools -p "test_*.py" && python3 tools/test_navigation_adapter.py --project-root /workspace' ;;
  export) exec python3 tools/export_project.py "$@" ;;
  sim|mission|loop|stop)
    RUN_ID=${1:?Specify a new run id, for example room-demo-01}
    [[ "$RUN_ID" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$ ]] || { echo 'Invalid run id' >&2; exit 2; }
    CONTAINER="d435i-$RUN_ID"
    if [[ "$ACTION" == stop ]]; then exec docker stop -t 15 "$CONTAINER"; fi
    if [[ "$ACTION" == mission ]]; then exec docker exec "$CONTAINER" bash /workspace/tools/mission_runtime.sh "$RUN_ID" "${2:-config/components/navigation/room_crossing_goal.json}"; fi
    if [[ "$ACTION" == loop ]]; then exec docker exec "$CONTAINER" bash /workspace/tools/loop_runtime.sh "$RUN_ID" "${2:-config/components/localization/loop_observer.json}"; fi
    require_image
    [[ ! -e "artifacts/runs/$RUN_ID" ]] || { echo 'Refusing to reuse run directory' >&2; exit 9; }
    [[ -z "$(docker ps -q --filter "label=d435i.project=$ROOT")" ]] || { echo 'Stop the active project simulation first' >&2; exit 9; }
    GUI=()
    if [[ "${2:-}" == --gui ]]; then
      AUTH=${XAUTHORITY:-}
      if [[ -z "$AUTH" ]]; then
        for candidate in /run/user/"$(id -u)"/.mutter-Xwaylandauth.* "$HOME/.Xauthority"; do
          if [[ -r "$candidate" ]]; then AUTH=$candidate; break; fi
        done
      fi
      [[ -r "$AUTH" ]] || { echo 'Set XAUTHORITY to the readable desktop X11 authority file' >&2; exit 2; }
      GUI=(-e "DISPLAY=${DISPLAY:-:0}" -e XAUTHORITY=/tmp/project.xauth -e PROJECT_GUI=1 -v "$AUTH:/tmp/project.xauth:ro" -v /tmp/.X11-unix:/tmp/.X11-unix:ro)
    elif [[ -n "${2:-}" ]]; then echo 'Usage: project.sh sim RUN_ID [--gui]' >&2; exit 2; fi
    DOMAIN=$(read_config ros_domain_id)
    GPU_ARGS=(--gpus all)
    GPU_REQUESTED=all
    GPU_UUIDS=()
    if [[ -n "${PROJECT_GPU_DEVICE:-}" ]]; then
      [[ "$PROJECT_GPU_DEVICE" =~ ^[0-9]+$ ]] || { echo 'PROJECT_GPU_DEVICE must be a host GPU index from nvidia-smi' >&2; exit 2; }
      GPU_UUID=$(nvidia-smi -i "$PROJECT_GPU_DEVICE" --query-gpu=uuid --format=csv,noheader 2>/dev/null | head -n1)
      [[ -n "$GPU_UUID" ]] || { echo "Host GPU index $PROJECT_GPU_DEVICE is unavailable" >&2; exit 2; }
      GPU_ARGS=(--gpus "device=$PROJECT_GPU_DEVICE")
      GPU_REQUESTED=$PROJECT_GPU_DEVICE
      GPU_UUIDS=("$GPU_UUID")
    else
      while IFS= read -r GPU_UUID; do
        [[ -z "$GPU_UUID" ]] || GPU_UUIDS+=("$GPU_UUID")
      done < <(nvidia-smi --query-gpu=uuid --format=csv,noheader 2>/dev/null || true)
    fi
    mkdir -p "artifacts/runs/$RUN_ID"
    python3 - "$RUN_ID" "$GPU_REQUESTED" "${GPU_UUIDS[@]}" <<'PY'
import json
from pathlib import Path
import sys

run_id, requested, *uuids = sys.argv[1:]
Path('artifacts/runs', run_id, 'gpu-request.json').write_text(
    json.dumps({'requested_host_index': requested,
                'requested_host_uuids': uuids}, indent=2) + '\n',
    encoding='utf-8')
PY
    docker run -d "${GPU_ARGS[@]}" --name "$CONTAINER" --label "d435i.project=$ROOT" --network host --ipc host --shm-size=512m \
      -e "VINS_DIAGNOSTIC_COST_GROUPS=${VINS_DIAGNOSTIC_COST_GROUPS:-1}" -e NVIDIA_DRIVER_CAPABILITIES=all -e "ROS_DOMAIN_ID=$DOMAIN" -e ROS_LOCALHOST_ONLY=0 \
      -e "D435I_SENSOR_BRIDGE_CONFIG=${D435I_SENSOR_BRIDGE_CONFIG:-}" \
      -e "GZ_PARTITION=d435i_$RUN_ID" -e GZ_IP=127.0.0.1 "${GUI[@]}" \
      -v "$ROOT:/workspace:rw" -w /workspace "$IMAGE" bash tools/sim_runtime.sh "$RUN_ID"
    ;;
  *) echo 'Usage: tools/project.sh {fetch|build [all|ros|px4]|test|sim RUN_ID [--gui]|loop RUN_ID|mission RUN_ID|stop RUN_ID|export OUTPUT}' ;;
esac
