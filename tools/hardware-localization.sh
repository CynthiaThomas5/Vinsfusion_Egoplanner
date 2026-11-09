#!/usr/bin/env bash
# Start the session-bound VINS/localization pair on the Nano; never starts sensors or control.
set -eo pipefail
workspace=$(cd "$(dirname "$0")/.." && pwd)
state_file="$workspace/.runtime/hw04-localization.state"

hardware_env() {
  source /opt/ros/foxy/setup.bash
  export HW_REALSENSE_OVERLAY=${HW_REALSENSE_OVERLAY:-$(python3 "$workspace/tools/hardware_profile.py" --realsense-value overlay)}
  export HW_REALSENSE_SDK_LIB=${HW_REALSENSE_SDK_LIB:-$(python3 "$workspace/tools/hardware_profile.py" --realsense-value sdk_lib)}
  source "$HW_REALSENSE_OVERLAY"
  export HW_HARDWARE_INSTALL=${HW_HARDWARE_INSTALL:-$(python3 "$workspace/tools/hardware_profile.py" --install-base)}
  source "$HW_HARDWARE_INSTALL/local_setup.bash"
  if [[ -n "${HW_SESSION_ID:-}" ]]; then
    python3 "$workspace/tools/hardware_profile.py" --session-preflighted "$HW_SESSION_ID" || {
      echo 'Hardware session does not own the selected install prefix.' >&2
      return 1
    }
  else
    python3 "$workspace/tools/check_hardware_install.py"
  fi
  local prefix=${HW_DEPENDENCY_PREFIX:-/home/jetson/realsense_debug/vins_integration}
  local sdk_lib=$HW_REALSENSE_SDK_LIB
  export LD_LIBRARY_PATH="$prefix/ceres21/lib:$prefix/opencv42/usr/lib/aarch64-linux-gnu:$sdk_lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export FASTRTPS_DEFAULT_PROFILES_FILE=${HW_FASTDDS_PROFILE:-/home/jetson/realsense_debug/fastdds_rgbd.xml}
  export OMP_NUM_THREADS=2 OMP_WAIT_POLICY=PASSIVE
}

read_state() {
  mapfile -t state < "$state_file"
  wrapper_pid=${state[0]:-}
  vins_pid=${state[1]:-}
  adapter_pid=${state[2]:-}
  epoch=${state[3]:-}
  session_dir=${state[4]:-}
  run_dir=${state[5]:-}
}

case "${1:-}" in
  start)
    if [[ -e "$workspace/.runtime/hardware-session.json" && -z "${HW_SESSION_ID:-}" ]]; then
      echo 'A unified hardware session or build owns the runtime; use its lifecycle command.' >&2
      exit 1
    fi
    shift
    session_dir=${1:-}
    [[ "$(uname -m)" == aarch64 ]] || { echo 'Must run on the Jetson Nano (aarch64).' >&2; exit 2; }
    [[ -n "$session_dir" ]] || { echo 'Usage: tools/hardware-localization.sh start SESSION_DIR' >&2; exit 2; }
    session_dir=$(realpath "$session_dir")
    case "$session_dir/" in "$workspace/artifacts/runs/"*) ;; *) echo 'Session must be inside this workspace artifacts/runs.' >&2; exit 2 ;; esac
    [[ -s "$session_dir/session.json" && -s "$session_dir/vins.yaml" ]] || { echo 'Session manifest or VINS YAML is missing.' >&2; exit 2; }
    vins_profile=${HW_VINS_FASTDDS_PROFILE:-${HW_FASTDDS_PROFILE:-$workspace/config/hardware/vins_fastdds_udp_rxbuf4m.xml}}
    if [[ "$(basename "$vins_profile")" == "vins_fastdds_udp_rxbuf4m.xml" ]]; then
      rmem_max=$(cat /proc/sys/net/core/rmem_max)
      if (( rmem_max < 8388608 )); then
        echo "VINS UDP profile requests a 4 MiB receive buffer; tested Nano requires net.core.rmem_max >= 8388608 (current: $rmem_max). Set it with 'sudo sysctl -w net.core.rmem_max=8388608' before start and restore the prior value after stop." >&2
        exit 2
      fi
    fi
    [[ -s "$workspace/.runtime/hardware-sensors.state" ]] || { echo 'Start the owned D435i sensor session first.' >&2; exit 1; }
    if [[ -s "$state_file" ]]; then echo 'An HW04 localization state exists; inspect status/stop first.' >&2; exit 1; fi
    hardware_env
    python3 - "$workspace" <<'PY'
import importlib
from pathlib import Path
import sys
root = Path(sys.argv[1])
for name in ('node', 'health', 'image_metadata'):
    module = importlib.import_module('uav_localization.' + name)
    source = root / 'src/own/uav_localization/uav_localization' / (name + '.py')
    if Path(module.__file__).read_bytes() != source.read_bytes():
        raise SystemExit('Installed localization differs from source: ' + name
                         + '; rebuild with a fresh package build directory before starting')
PY
    identity=$(python3 - "$session_dir/session.json" <<'PY'
import json, re, sys
session = json.load(open(sys.argv[1]))
epoch = session.get('epoch', '')
if not re.fullmatch(r'[0-9a-f]{32}', epoch) or session.get('namespace') != '/vins_raw/s_' + epoch:
    raise SystemExit('Invalid session identity')
if session.get('rig_config') != 'config/hardware/rig.json':
    raise SystemExit('Refusing a non-hardware rig session')
print(epoch)
PY
    )
    if ps -eo comm=,args= | awk '$1 == "vins_node" || ($1 == "python3" && ($0 ~ /vins_node/ || $0 ~ /localization_adapter/)) { found = 1 } END { exit !found }'; then
      echo 'VINS or localization is already running; refusing duplicate ownership.' >&2
      exit 1
    fi
    opencv_threads=$(python3 - "$session_dir/session.json" "$workspace" <<'PYTHREADS'
import hashlib, json, sys
from pathlib import Path
session = json.load(open(sys.argv[1]))
relative = Path(session['settings_config'])
if relative.is_absolute() or '..' in relative.parts:
    raise SystemExit('Invalid session settings path')
settings = Path(sys.argv[2])/relative
if hashlib.sha256(settings.read_bytes()).hexdigest() != session['settings_sha256']:
    raise SystemExit('Session settings hash changed')
count = json.loads(settings.read_text()).get('opencv_threads')
if (type(count) is not int or not 1 <= count <= 4
        or session.get('runtime', {}).get('opencv_threads') != count):
    raise SystemExit('Session OpenCV thread setting is missing or differs from canonical settings')
print(count)
PYTHREADS
    )
    export VINS_OPENCV_THREADS="$opencv_threads"
    run_dir=$(dirname "$session_dir")
    mkdir -p "$workspace/.runtime"
    setsid bash -c 'source /opt/ros/foxy/setup.bash; source "$HW_REALSENSE_OVERLAY"; source "$HW_HARDWARE_INSTALL/local_setup.bash"; prefix=${HW_DEPENDENCY_PREFIX:-/home/jetson/realsense_debug/vins_integration}; export LD_LIBRARY_PATH="$prefix/ceres21/lib:$prefix/opencv42/usr/lib/aarch64-linux-gnu:$HW_REALSENSE_SDK_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"; export FASTRTPS_DEFAULT_PROFILES_FILE=${HW_VINS_FASTDDS_PROFILE:-${HW_FASTDDS_PROFILE:-$1/config/hardware/vins_fastdds_udp_rxbuf4m.xml}}; export OMP_NUM_THREADS=2 OMP_WAIT_POLICY=PASSIVE; exec ros2 run vins vins_node "$2/vins.yaml" --ros-args -r "__ns:=/vins_raw/s_$3" -p use_sim_time:=false' _ "$workspace" "$session_dir" "$identity" > "$run_dir/vins.log" 2>&1 < /dev/null &
    vins_pid=$!
    # Wait for VINS to expose its epoch-scoped publisher before creating the
    # adapter participant; an alive ros2-run wrapper alone is not readiness.
    vins_topic="/vins_raw/s_$identity/odometry"
    vins_ready=false
    for _ in $(seq 1 10); do
      if ! kill -0 "$vins_pid" 2>/dev/null; then break; fi
      if ros2 topic info "$vins_topic" 2>/dev/null | grep -q 'Publisher count: 1'; then
        vins_ready=true
        break
      fi
      sleep 1
    done
    if [[ "$vins_ready" != true ]]; then
      if kill -0 -- "-$vins_pid" 2>/dev/null; then
        [[ "$(ps -o pgid= -p "$vins_pid" 2>/dev/null | tr -d ' ')" == "$vins_pid" ]] || { echo 'Refusing to signal VINS: recorded process group is not owned.' >&2; exit 1; }
        ps -o args= -g "$vins_pid" | grep -q 'vins_node' || { echo 'Recorded VINS process group identity changed.' >&2; exit 1; }
        kill -TERM -- "-$vins_pid"
        for _ in $(seq 1 10); do
          if ! kill -0 -- "-$vins_pid" 2>/dev/null; then break; fi
          sleep 0.2
        done
      fi
      echo "VINS did not publish $vins_topic within 10 seconds; stopped the unready VINS process group. Inspect $run_dir/vins.log." >&2
      exit 1
    fi
    setsid bash -c 'source /opt/ros/foxy/setup.bash; source "$HW_REALSENSE_OVERLAY"; source "$HW_HARDWARE_INSTALL/local_setup.bash"; prefix=${HW_DEPENDENCY_PREFIX:-/home/jetson/realsense_debug/vins_integration}; export LD_LIBRARY_PATH="$prefix/ceres21/lib:$prefix/opencv42/usr/lib/aarch64-linux-gnu:$HW_REALSENSE_SDK_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"; export FASTRTPS_DEFAULT_PROFILES_FILE=${HW_ADAPTER_FASTDDS_PROFILE:-${HW_FASTDDS_PROFILE:-$1/config/hardware/vins_fastdds_udp_rxbuf4m.xml}}; export OMP_NUM_THREADS=2 OMP_WAIT_POLICY=PASSIVE; exec ros2 run uav_localization localization_adapter --ros-args -p project_root:="$1" -p session_manifest:="$2/session.json" -p use_sim_time:=false' _ "$workspace" "$session_dir" > "$run_dir/localization.log" 2>&1 < /dev/null &
    adapter_pid=$!
    printf '%s\n%s\n%s\n%s\n%s\n%s\n' "$$" "$vins_pid" "$adapter_pid" "$identity" "$session_dir" "$run_dir" > "$state_file"
    sleep 3
    if ! kill -0 "$vins_pid" 2>/dev/null || ! kill -0 "$adapter_pid" 2>/dev/null; then
      echo 'VINS or localization exited during startup; inspect run logs; state retained.' >&2
      exit 1
    fi
    printf 'started epoch=%s vins_pid=%s localization_pid=%s\nrun_dir=%s\n' "$identity" "$vins_pid" "$adapter_pid" "$run_dir"
    ;;
  status)
    hardware_env
    if [[ ! -s "$state_file" ]]; then echo 'No HW04 localization session owned by this workspace.'; exit 0; fi
    read_state
    printf 'epoch=%s vins_pid=%s localization_pid=%s session=%s\n' "$epoch" "$vins_pid" "$adapter_pid" "$session_dir"
    ps -o pid,pgid,args -p "$vins_pid","$adapter_pid" || true
    ros2 node list
    ros2 topic list -t | grep -E '^/localization/|^/vins_raw/s_' || true
    ;;
  stop)
    if [[ -e "$workspace/.runtime/hardware-session.json" && -z "${HW_SESSION_ID:-}" ]]; then
      echo 'A unified hardware session owns localization; stop it through the session command.' >&2
      exit 1
    fi
    [[ -s "$state_file" ]] || { echo 'No HW04 localization session owned by this workspace.'; exit 0; }
    read_state
    [[ "$(ps -o pgid= -p "$adapter_pid" 2>/dev/null | tr -d ' ')" == "$adapter_pid" ]] || { echo 'Refusing to signal localization: recorded process group is not owned.' >&2; exit 1; }
    ps -o args= -g "$adapter_pid" | grep -q 'localization_adapter' || { echo 'Recorded localization process group identity changed.' >&2; exit 1; }
    if kill -0 -- "-$vins_pid" 2>/dev/null; then
      [[ "$(ps -o pgid= -p "$vins_pid" 2>/dev/null | tr -d ' ')" == "$vins_pid" ]] || { echo 'Refusing to signal VINS: recorded process group is not owned.' >&2; exit 1; }
      ps -o args= -g "$vins_pid" | grep -q 'vins_node' || { echo 'Recorded VINS process group identity changed.' >&2; exit 1; }
      kill -TERM -- "-$vins_pid"
      for _ in $(seq 1 10); do
        if ! kill -0 -- "-$vins_pid" 2>/dev/null; then break; fi
        sleep 0.2
      done
    fi
    vins_stop_wall_epoch_s=$(date +%s.%N)
    policy="$workspace/config/components/localization/health_hardware.json"
    gate=false
    if [[ -r "$policy" ]]; then
      gate=$(python3 - "$policy" <<'PY'
import json, sys
policy = json.load(open(sys.argv[1]))
print(policy.get('freshness', {}).get('mode') == 'gate')
PY
      ) || gate=unknown
    else
      gate=unknown
    fi
    invalid_observed=not_required
    if [[ "$gate" == True ]]; then
      was_valid=false
      if python3 - "$run_dir/localization.log" "$epoch" "$vins_stop_wall_epoch_s" <<'PY'
import json, sys
path, epoch, stopped = sys.argv[1], sys.argv[2], float(sys.argv[3])
for line in open(path, errors='replace'):
    marker = 'localization_age_observation '
    if marker not in line:
        continue
    try:
        observation = json.loads(line.split(marker, 1)[1])
    except json.JSONDecodeError:
        continue
    if (observation.get('epoch') == epoch
            and observation.get('wall_epoch_s', 0) < stopped
            and observation.get('status', {}).get('valid') is True):
        raise SystemExit(0)
raise SystemExit(1)
PY
      then
        was_valid=true
      fi
      if [[ "$was_valid" == true ]]; then
        observed=false
        for _ in $(seq 1 20); do
          if python3 - "$run_dir/localization.log" "$epoch" "$vins_stop_wall_epoch_s" <<'PY'
import json, sys
path, epoch, stopped = sys.argv[1], sys.argv[2], float(sys.argv[3])
for line in open(path, errors='replace'):
    marker = 'localization_age_observation '
    if marker not in line:
        continue
    try:
        observation = json.loads(line.split(marker, 1)[1])
    except json.JSONDecodeError:
        continue
    if (observation.get('epoch') == epoch
            and observation.get('wall_epoch_s', 0) >= stopped
            and observation.get('status', {}).get('valid') is False):
        print(observation['status'].get('reason', 'invalid'))
        raise SystemExit(0)
raise SystemExit(1)
PY
          then
            observed=true
            break
          fi
          sleep 0.5
        done
        if [[ "$observed" != true ]]; then
          echo 'Stopped VINS, but the adapter did not log invalid localization for the active epoch.' >&2
          exit 1
        fi
        invalid_observed=adapter_log_after_vins_stop
      else
        invalid_observed=not_qualified_no_valid_before_stop
      fi
    elif [[ "$gate" == unknown ]]; then
      invalid_observed=policy_unavailable
    fi
    kill -TERM -- "-$adapter_pid"
    for _ in $(seq 1 15); do
      if ! kill -0 -- "-$adapter_pid" 2>/dev/null; then break; fi
      sleep 0.2
    done
    if kill -0 -- "-$adapter_pid" 2>/dev/null || kill -0 -- "-$vins_pid" 2>/dev/null; then
      echo 'HW04 localization process group did not stop; state retained.' >&2
      exit 1
    fi
    rm -f "$state_file"
    printf 'stopped epoch=%s; invalid_status_observed=%s; D435i sensor process remains owned separately\n' "$epoch" "$invalid_observed"
    ;;
  *)
    echo 'Usage: tools/hardware-localization.sh {start SESSION_DIR|status|stop}' >&2
    exit 2
    ;;
esac
