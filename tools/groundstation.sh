#!/usr/bin/env bash
# Debian host entrypoint. Estimation, mapping and planning remain on the Nano.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
source "$root/config/groundstation/debian.env"
state=${XDG_STATE_HOME:-$HOME/.local/state}/d435i-groundstation
mkdir -p "$state"

nano() { ssh "$GS_NANO_HOST" "$@"; }
session() { nano "cd '$GS_NANO_ROOT' && bash tools/hardware.sh status"; }
ros_run() {
  local domain=$1; shift
  docker run --rm --init --network host --ipc host \
    --user "$(id -u):$(id -g)" -e HOME="$HOME" \
    -e ROS_DOMAIN_ID="$domain" -e ROS_LOCALHOST_ONLY=0 \
    -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp -e PYTHONUNBUFFERED=1 \
    -v "$root:/workspace" -v "$HOME/.ssh:$HOME/.ssh:ro" \
    -v "$state:$state" -w /workspace "$GS_IMAGE" \
    bash -c 'source /opt/ros/jazzy/setup.bash; source /opt/uav-venv/bin/activate; source /opt/uav-interfaces/setup.bash; exec "$@"' _ "$@"
}
display_env() {
  # Desktop launch and SSH use the logged-in user's Xwayland credentials.
  local envs
  envs=$(systemctl --user show-environment)
  display=$(printf '%s\n' "$envs" | sed -n 's/^DISPLAY=//p')
  auth=$(printf '%s\n' "$envs" | sed -n 's/^XAUTHORITY=//p')
  [[ -n "$display" && -r "$auth" ]] || { echo 'Log in to the graphical desktop first.' >&2; return 1; }
}
gui_run() {
  local name=$1 domain=$2; shift 2
  display_env
  docker run --rm --init --name "$name" --network host --ipc host \
    --user "$(id -u):$(id -g)" --device /dev/dri \
    --group-add "$(stat -c %g /dev/dri/renderD128)" \
    -e HOME="$HOME" -e DISPLAY="$display" -e XAUTHORITY="$auth" \
    -e QT_QPA_PLATFORM=xcb -e QT_X11_NO_MITSHM=1 \
    -e ROS_DOMAIN_ID="$domain" -e ROS_LOCALHOST_ONLY=0 \
    -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp -e PYTHONUNBUFFERED=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro -v "$auth:$auth:ro" \
    -v "$root:/workspace" -v "$HOME/.ssh:$HOME/.ssh:ro" \
    -v "$state:$state" -w /workspace "$GS_IMAGE" \
    bash -c 'source /opt/ros/jazzy/setup.bash; source /opt/uav-venv/bin/activate; source /opt/uav-interfaces/setup.bash; exec "$@"' _ "$@"
}

case "${1:-help}" in
  check)
    docker image inspect "$GS_IMAGE" --format '{{.Id}}'
    nano 'hostname; uname -m'
    ros_run "$GS_VIEW_DOMAIN" python3 -c 'import rclpy,cv2; from pymavlink.dialects.v20 import common; from uav_interfaces.action import NavigateToPose; print("Groundstation imports PASS")'
    session
    ;;
  status) session; docker ps --filter name=d435i-gs --format '{{.Names}} {{.Status}}' ;;
  view)
    shift
    info=$(session)
    run=$(printf '%s' "$info" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["run_dir"])')
    if [[ "${1:-}" == --visuals ]]; then
      nano "pgrep -f '^python3 tools/diagnostics/relay_vins_visuals.py' >/dev/null && exit 1 || exit 0" || {
        echo 'A visualization relay already exists. Close its owning viewer before starting a second full viewer.' >&2; exit 1;
      }
    elif (($#)); then echo 'Usage: groundstation.sh view [--visuals]' >&2; exit 2; fi
    # One container owns both local processes; stopping it closes its SSH streams.
    gui_run d435i-gs-view "$GS_VIEW_DOMAIN" bash -c '
      python3 tools/diagnostics/hardware_live_rviz.py --live --vins-only \
        --nano-host "$1" --remote-root "$2" --run-path "$3" --status-file "$4" "${@:5}" &
      view=$!
      rviz2 -d config/rviz/hardware_live.rviz &
      rviz=$!
      trap '\''kill -TERM "$view" "$rviz" 2>/dev/null || true; wait || true'\'' EXIT
      trap '\''exit 0'\'' INT TERM HUP
      wait -n "$view" "$rviz"
    ' _ "$GS_NANO_HOST" "$GS_NANO_ROOT" "$run" "$state/live-status.json" "$@"
    ;;
  map-view)
    info=$(session)
    run=$(printf '%s' "$info" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["run_dir"])')
    gui_run d435i-gs-map "$GS_VIEW_DOMAIN" bash -c '
      python3 tools/diagnostics/groundstation_map.py view --host "$1" --root "$2" --run "$3" --relay-domain "$4" &
      relay=$!
      rviz2 -d config/rviz/groundstation_map.rviz &
      rviz=$!
      trap '\''kill -TERM "$relay" "$rviz" 2>/dev/null || true; wait || true'\'' EXIT
      trap '\''exit 0'\'' INT TERM HUP
      wait -n "$relay" "$rviz"
    ' _ "$GS_NANO_HOST" "$GS_NANO_ROOT" "$run" "$GS_NANO_DOMAIN"
    ;;
  rviz) shift; gui_run d435i-gs-rviz "$GS_VIEW_DOMAIN" rviz2 "$@" ;;
  stop-view)
    for name in d435i-gs-view d435i-gs-map; do
      if docker inspect "$name" >/dev/null 2>&1; then docker stop -t 15 "$name"; fi
    done
    ;;
  experiment-start)
    name=d435i-gs-view
    if docker inspect "$name" >/dev/null 2>&1; then
      if [[ $(docker inspect --format '{{.State.Running}}' "$name") == true ]]; then
        echo 'A groundstation viewer already exists; inspect status and close its owner first.' >&2; exit 1
      fi
      echo 'Removing an exited groundstation viewer after printing its retained log:' >&2
      docker logs "$name" >&2 || true
      docker rm "$name" >/dev/null
    fi
    info=$(session)
    if [[ "$info" == \{* ]]; then
      echo 'A Nano session already exists; inspect status and stop it before starting this experiment.' >&2; exit 1
    fi
    run_id="hw10-groundstation-$(date -u +%Y%m%dT%H%M%SZ)"
    run="$GS_NANO_ROOT/artifacts/runs/$run_id"
    display_env
    docker run --init --detach --name "$name" --network host --ipc host \
      --user "$(id -u):$(id -g)" --device /dev/dri \
      --group-add "$(stat -c %g /dev/dri/renderD128)" \
      -e HOME="$HOME" -e DISPLAY="$display" -e XAUTHORITY="$auth" \
      -e QT_QPA_PLATFORM=xcb -e QT_X11_NO_MITSHM=1 \
      -e ROS_DOMAIN_ID="$GS_VIEW_DOMAIN" -e ROS_LOCALHOST_ONLY=0 \
      -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp -e PYTHONUNBUFFERED=1 \
      -v /tmp/.X11-unix:/tmp/.X11-unix:ro -v "$auth:$auth:ro" \
      -v "$root:/workspace" -v "$HOME/.ssh:$HOME/.ssh:ro" \
      -v "$state:$state" -w /workspace "$GS_IMAGE" bash -c '
        set -eo pipefail
        source /opt/ros/jazzy/setup.bash
        source /opt/uav-venv/bin/activate
        source /opt/uav-interfaces/setup.bash
        python3 tools/diagnostics/hardware_live_rviz.py --live --vins-only --visuals \
          --nano-host "$1" --remote-root "$2" --run-path "$3" --status-file "$4" \
          --status-samples-file "artifacts/runs/$5/viewer-status-samples.jsonl" \
          --visual-events-file "artifacts/runs/$5/visual-receive-events.jsonl" &
        view=$!
        rviz2 -d config/rviz/hardware_live.rviz &
        rviz=$!
        python3 tools/diagnostics/record_vins_circle.py --output "artifacts/runs/$5/groundstation" &
        recorder=$!
        trap '\''kill -TERM "$view" "$rviz" "$recorder" 2>/dev/null || true; wait || true'\'' EXIT
        trap '\''exit 0'\'' INT TERM HUP
        wait -n "$view" "$rviz" "$recorder"
      ' _ "$GS_NANO_HOST" "$GS_NANO_ROOT" "$run" "$state/$run_id-live-status.json" "$run_id"
    ready=false
    for _ in $(seq 1 60); do
      if [[ $(docker inspect --format '{{.State.Running}}' "$name" 2>/dev/null || true) != true ]]; then
        echo 'Groundstation viewer exited before relay startup; container log follows:' >&2
        docker logs "$name" >&2 || true
        docker rm "$name" >/dev/null 2>&1 || true
        echo 'Groundstation viewer exited before relay startup.' >&2; exit 1
      fi
      if ssh -o BatchMode=yes "$GS_NANO_HOST" \
          "pgrep -af '[r]elay_vins_visuals.py' | grep -F -- '$run' | wc -l | grep -qx 2"; then
        ready=true; break
      fi
      sleep 1
    done
    if [[ "$ready" != true ]]; then
      docker stop -t 10 "$name" >/dev/null 2>&1 || true
      docker logs "$name" >&2 || true
      docker rm "$name" >/dev/null 2>&1 || true
      echo 'Nano visualization relays did not start; perception was not started.' >&2; exit 1
    fi
    nano "cd '$GS_NANO_ROOT' && bash tools/hardware.sh start perception --visuals --run-id '$run_id'"
    ready=false
    for _ in $(seq 1 120); do
      if docker exec "$name" test -s "/workspace/artifacts/runs/$run_id/groundstation/circle-ready.json"; then
        ready=true; break
      fi
      if ! docker inspect "$name" >/dev/null 2>&1; then break; fi
      sleep 1
    done
    if [[ "$ready" != true ]]; then
      echo "Nano perception started; circle baseline is not ready. Check status before moving (run $run_id)." >&2; exit 1
    fi
    echo "VINS定位有效，静止起点已记录。可以开始慢速绕圈；运行ID：$run_id"
    ;;
  experiment-stop)
    info=$(session)
    run_id=
    if [[ "$info" == \{* ]]; then
      layer=$(printf '%s' "$info" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["layer"])')
      [[ "$layer" == perception ]] || { echo "Refusing experiment-stop for Nano layer $layer; use its qualified stop procedure." >&2; exit 1; }
      run_id=$(printf '%s' "$info" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin).get("run_id", ""))')
      nano "cd '$GS_NANO_ROOT' && bash tools/hardware.sh stop"
    fi
    if docker inspect d435i-gs-view >/dev/null 2>&1; then
      docker stop -t 15 d435i-gs-view
      if [[ -n "$run_id" ]]; then
        mkdir -p "$root/artifacts/runs/$run_id/groundstation"
        docker logs d435i-gs-view > "$root/artifacts/runs/$run_id/groundstation/viewer-console.log" 2>&1 || true
      fi
      docker rm d435i-gs-view >/dev/null
    fi
    ;;
  nano-start)
    case "${2:-}" in perception|map|plan) nano "cd '$GS_NANO_ROOT' && bash tools/hardware.sh start '$2'" ;;
      *) echo 'Usage: groundstation.sh nano-start {perception|map|plan}' >&2; exit 2;; esac
    ;;
  nano-stop) nano "cd '$GS_NANO_ROOT' && bash tools/hardware.sh stop" ;;
  nano-shell) exec ssh -t "$GS_NANO_HOST" ;;
  telemetry)
    # Refuse serial contention. No serial owner is stopped automatically.
    nano 'test -e /dev/ttyACM0 && ! fuser /dev/ttyACM0 >/dev/null 2>&1' || {
      echo 'Nano USB serial is absent or busy. Do not run alongside Agent or another serial reader.' >&2; exit 1;
    }
    echo 'Receive-only QGC telemetry: QGC commands and parameter requests are NOT forwarded.'
    exec /usr/bin/python3 "$root/tools/diagnostics/qgc_readonly.py" --host "$GS_NANO_HOST" --root "$GS_NANO_ROOT"
    ;;
  nano-ros)
    shift
    printf -v command '%q ' "$@"
    nano "cd '$GS_NANO_ROOT'; source tools/hardware-env.bash; export FASTRTPS_DEFAULT_PROFILES_FILE=\"\$PWD/config/hardware/vins_fastdds_udp_rxbuf4m.xml\"; exec ros2 $command"
    ;;
  ros) shift; exec "$0" nano-ros "$@" ;;
  local-ros) shift; ros_run "$GS_VIEW_DOMAIN" ros2 "$@" ;;
  qgc)
    display_env
    qgc="$root/../downloads/QGroundControl-v5.0.8-x86_64.AppImage"
    [[ -x "$qgc" ]] || { echo "Missing executable: $qgc" >&2; exit 1; }
    exec env DISPLAY="$display" XAUTHORITY="$auth" QT_QPA_PLATFORM=xcb "$qgc" --appimage-extract-and-run
    ;;
  *) echo 'Usage: groundstation.sh {check|status|view [--visuals]|experiment-start|experiment-stop|map-view|stop-view|rviz ARGS|nano-start perception/plan|nano-stop|nano-shell|ros ARGS|local-ros ARGS|qgc|telemetry}' ;;
esac
