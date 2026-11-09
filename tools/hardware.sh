#!/usr/bin/env bash
# Native ARM/Foxy hardware entrypoints; build does not start sensor or PX4 processes.
set -eo pipefail
workspace=$(cd "$(dirname "$0")/.." && pwd)
cd "$workspace"

load_hardware_sdk_profile() {
  mapfile -t hardware_sdk_profile < <(python3 - "$workspace" <<'PYSDK'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'tools'))
from hardware_profile import read_realsense_deployment
profile=read_realsense_deployment(Path(sys.argv[1]))
for key in ('overlay','wrapper_source_dir','wrapper_prefix','wrapper_version',
            'wrapper_commit','wrapper_sha256','sdk_source_dir','sdk_patch',
            'sdk_patch_sha256','sdk_lib','sdk_version','sdk_commit','sdk_sha256'):
    print(profile[key])
PYSDK
  )
  [[ ${#hardware_sdk_profile[@]} == 13 ]] || { echo 'Invalid RealSense deployment profile'; return 2; }
  export HW_REALSENSE_OVERLAY=${HW_REALSENSE_OVERLAY:-${hardware_sdk_profile[0]}}
  export HW_REALSENSE_SOURCE_DIR=${HW_REALSENSE_SOURCE_DIR:-${hardware_sdk_profile[1]}}
  export HW_REALSENSE_WRAPPER_PREFIX=${HW_REALSENSE_WRAPPER_PREFIX:-${hardware_sdk_profile[2]}}
  export HW_REALSENSE_SDK_SOURCE_DIR=${HW_REALSENSE_SDK_SOURCE_DIR:-${hardware_sdk_profile[6]}}
  export HW_REALSENSE_SDK_PATCH=${HW_REALSENSE_SDK_PATCH:-${hardware_sdk_profile[7]}}
  export HW_REALSENSE_SDK_LIB=${HW_REALSENSE_SDK_LIB:-${hardware_sdk_profile[9]}}
  hardware_sdk_expected_wrapper_version=${hardware_sdk_profile[3]}
  hardware_sdk_expected_wrapper_commit=${hardware_sdk_profile[4]}
  hardware_sdk_expected_wrapper_sha=${hardware_sdk_profile[5]}
  hardware_sdk_expected_patch_sha=${hardware_sdk_profile[8]}
  hardware_sdk_expected_version=${hardware_sdk_profile[10]}
  hardware_sdk_expected_soname=${hardware_sdk_expected_version%.*}
  hardware_sdk_expected_commit=${hardware_sdk_profile[11]}
  hardware_sdk_expected_sha=${hardware_sdk_profile[12]}
}

hardware_sensor_env() {
  source /opt/ros/foxy/setup.bash
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
  local sdk_lib=$HW_REALSENSE_SDK_LIB
  export LD_LIBRARY_PATH="$sdk_lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export FASTRTPS_DEFAULT_PROFILES_FILE=${HW_FASTDDS_PROFILE:-/home/jetson/realsense_debug/fastdds_rgbd.xml}
  export OMP_NUM_THREADS=2 OMP_WAIT_POLICY=PASSIVE
}

sensors_command() {
  local operation=${1:-}
  local state_file="$workspace/.runtime/hardware-sensors.state"
  if [[ "$operation" == start || "$operation" == status ]]; then
    load_hardware_sdk_profile || return $?
  fi
  local source_dir=$HW_REALSENSE_SOURCE_DIR
  local sdk_source_dir=$HW_REALSENSE_SDK_SOURCE_DIR
  local sdk_patch_file=$HW_REALSENSE_SDK_PATCH
  local wrapper_prefix=$HW_REALSENSE_WRAPPER_PREFIX
  local sdk_lib=$HW_REALSENSE_SDK_LIB

  case "$operation" in
    start)
      if [[ "$(uname -m)" != aarch64 ]]; then
        echo 'sensors start must run on the Jetson Nano (aarch64).' >&2
        return 2
      fi
      [[ -r /opt/ros/foxy/setup.bash ]] || { echo 'ROS Foxy is unavailable.' >&2; return 2; }
      [[ -r "$HW_REALSENSE_OVERLAY" ]] || { echo 'The RealSense Foxy overlay in the hardware profile is unavailable.' >&2; return 2; }
      export HW_HARDWARE_INSTALL=${HW_HARDWARE_INSTALL:-$(python3 "$workspace/tools/hardware_profile.py" --install-base)}
      [[ -r "$HW_HARDWARE_INSTALL/local_setup.bash" ]] || { echo 'Build the hardware workspace first.' >&2; return 2; }
      [[ -r "$sdk_lib/librealsense2.so.$hardware_sdk_expected_version" ]] || { echo 'The pinned RealSense SDK library is unavailable.' >&2; return 2; }
      [[ -r "$wrapper_prefix/lib/librealsense2_camera.so" ]] || { echo 'The existing RealSense ROS wrapper library is unavailable.' >&2; return 2; }
      local rig_identity serial asic_expected
      mapfile -t rig_identity < <(python3 "$workspace/tools/hardware_profile.py" --device-identity)
      if [[ ${#rig_identity[@]} != 2 ]]; then
        echo 'Rig must define API and ASIC/USB serial identities.' >&2
        return 2
      fi
      serial=${rig_identity[0]}
      asic_expected=${rig_identity[1]}
      export HW_D435I_API_SERIAL="$serial"
      if [[ -s "$state_file" ]]; then
        echo 'A hardware sensor session state exists; use sensors status/stop before starting another.' >&2
        return 1
      fi

      hardware_sensor_env
      local wrapper_version wrapper_commit sdk_commit sdk_patch_sha sdk_sha wrapper_sha sdk_resolved
      wrapper_version=$(ros2 pkg xml realsense2_camera | sed -n 's:.*<version>\([^<]*\)</version>.*:\1:p' | sed -n '1p')
      wrapper_commit=$(git -C "$source_dir" rev-parse HEAD 2>/dev/null || true)
      sdk_commit=$(git -C "$sdk_source_dir" rev-parse HEAD 2>/dev/null || true)
      sdk_patch_sha=$(sha256sum "$sdk_patch_file" 2>/dev/null | awk '{print $1}')
      sdk_sha=$(sha256sum "$sdk_lib/librealsense2.so.$hardware_sdk_expected_version" | awk '{print $1}')
      wrapper_sha=$(sha256sum "$wrapper_prefix/lib/librealsense2_camera.so" | awk '{print $1}')
      sdk_resolved=$(ldd "$wrapper_prefix/lib/librealsense2_camera.so" | awk '/librealsense2\.so/ && !found {print $3; found=1}')
      if [[ "$wrapper_version" != "$hardware_sdk_expected_wrapper_version" || "$wrapper_commit" != "$hardware_sdk_expected_wrapper_commit" || \
            "$sdk_commit" != "$hardware_sdk_expected_commit" || \
            "$sdk_patch_sha" != "$hardware_sdk_expected_patch_sha" || \
            "$sdk_sha" != "$hardware_sdk_expected_sha" || \
            "$wrapper_sha" != "$hardware_sdk_expected_wrapper_sha" || \
            "$sdk_resolved" != "$sdk_lib/librealsense2.so.$hardware_sdk_expected_soname" ]]; then
        echo "Unexpected RealSense load chain: wrapper=$wrapper_version source=$wrapper_commit sha=$wrapper_sha sdk_source=$sdk_commit patch=$sdk_patch_sha sdk_sha=$sdk_sha resolved=$sdk_resolved" >&2
        return 1
      fi
      if [[ -n "$(git -C "$source_dir" status --short 2>/dev/null)" ]]; then
        echo 'RealSense wrapper source is modified; refusing to use an unrecorded source state.' >&2
        return 1
      fi
      if [[ -n "$(git -C "$sdk_source_dir" status --short 2>/dev/null)" ]]; then
        echo 'RealSense SDK source is modified; refusing to use an unrecorded source state.' >&2
        return 1
      fi

      local devices observed_identity
      devices=$(rs-enumerate-devices -c 2>&1)
      if ! observed_identity=$(printf '%s\n' "$devices" | python3 "$workspace/tools/hardware_profile.py" \
            --match-device-identity --api-serial "$serial" --asic-usb-serial "$asic_expected"); then
        echo "Expected exactly one D435i API/ASIC serial pair matching the rig; enumeration was:" >&2
        printf '%s\n' "$devices" >&2
        return 1
      fi
      local observed=()
      mapfile -t observed <<< "$observed_identity"
      if [[ ${#observed[@]} != 3 ]]; then
        echo 'Could not read a complete API/ASIC/physical-port identity record.' >&2
        return 1
      fi
      serial=${observed[0]}
      asic_serial=${observed[1]}
      physical_port=${observed[2]}

      local device_nodes=() device props dev_pids
      for device in /dev/video* /dev/hidraw*; do
        [[ -e "$device" ]] || continue
        props=$(udevadm info --query=property --name="$device" 2>/dev/null || true)
        if [[ "$props" == *"$asic_serial"* ]]; then
          device_nodes+=("$device")
        fi
      done
      if ((${#device_nodes[@]} == 0)); then
        echo "Could not map any V4L/HID node to D435i API serial $serial / ASIC serial $asic_serial." >&2
        return 1
      fi
      for device in "${device_nodes[@]}"; do
        if dev_pids=$(fuser "$device" 2>/dev/null); then
          echo "D435i device node $device is already in use by PID(s): $dev_pids" >&2
          return 1
        fi
      done
      if pgrep -x realsense2_camera_node >/dev/null; then
        echo 'A RealSense camera node is already running; refusing duplicate ownership.' >&2
        return 1
      fi

      local run_id run_dir log_file
      run_id=${HW02_RUN_ID:-"hw02-$(date -u +%Y%m%dT%H%M%SZ)"}
      local enable_color=${HW02_ENABLE_COLOR:-false}
      if [[ "$enable_color" != true && "$enable_color" != false ]]; then
        echo 'HW02_ENABLE_COLOR must be true or false.' >&2
        return 2
      fi
      run_dir="$workspace/artifacts/runs/$run_id"
      log_file="$run_dir/sensors.log"
      mkdir -p "$run_dir" "$workspace/.runtime"
      printf 'D435i API serial: %s\nD435i ASIC/USB serial: %s\nPhysical port: %s\nWrapper version: %s\nWrapper source commit: %s\nWrapper library SHA256: %s\nSDK source commit: %s\nHID-hold/sensitivity patch SHA256: %s\nSDK library SHA256: %s\nRGB enabled: %s\n' \
        "$serial" "$asic_serial" "$physical_port" "$wrapper_version" "$wrapper_commit" "$wrapper_sha" "$sdk_commit" "$sdk_patch_sha" "$sdk_sha" "$enable_color" > "$run_dir/device-identity.txt"
      setsid bash -c 'source /opt/ros/foxy/setup.bash; source "$HW_REALSENSE_OVERLAY"; source "$HW_HARDWARE_INSTALL/local_setup.bash"; export LD_LIBRARY_PATH="$HW_REALSENSE_SDK_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"; export FASTRTPS_DEFAULT_PROFILES_FILE=${HW_FASTDDS_PROFILE:-/home/jetson/realsense_debug/fastdds_rgbd.xml}; export OMP_NUM_THREADS=2 OMP_WAIT_POLICY=PASSIVE; exec ros2 launch uav_sensor_interface d435i.launch.py "serial_no:=${HW_D435I_API_SERIAL}" "enable_color:=${HW02_ENABLE_COLOR:-false}" "depth_output_rate_hz:=${HW_DEPTH_OUTPUT_HZ:-0.0}"' _ "$workspace" >"$log_file" 2>&1 < /dev/null &
      local session_pid=$!
      printf '%s\n%s\n' "$session_pid" "$run_dir" > "$state_file"
      for _ in $(seq 1 40); do
        if ! kill -0 "$session_pid" 2>/dev/null; then
          echo 'D435i launch exited during startup; inspect the run log.' >&2
          rm -f "$state_file"
          return 1
        fi
        # ROS 2 CLI discovery depends on the daemon and can lag even while
        # the camera and C++ depth adapter are already publishing. Use the
        # launch processes' own readiness messages, then verify the loaded
        # SDK mapping below.
        if grep -q 'RealSense Node Is Up!' "$log_file" && grep -q 'First depth converted' "$log_file"; then
          local driver_pid loaded_libraries
          driver_pid=$(sed -n 's/.*realsense2_camera_node-1.*process started with pid \[\([0-9][0-9]*\)\].*/\1/p' "$log_file" | sed -n '1p')
          loaded_libraries="$run_dir/loaded-realsense-libraries.txt"
          if [[ -n "$driver_pid" ]] && [[ -r "/proc/$driver_pid/maps" ]]; then
            grep 'librealsense2' "/proc/$driver_pid/maps" > "$loaded_libraries" || true
          fi
          if [[ -z "$driver_pid" ]] || ! grep -Fq "$sdk_lib/librealsense2.so.$hardware_sdk_expected_soname" "$loaded_libraries" 2>/dev/null || ! grep -Fq "Running with LibRealSense v$hardware_sdk_expected_version" "$log_file"; then
            echo "The running camera process does not map the pinned SDK $hardware_sdk_expected_version library; stopping only this launch session." >&2
            kill -TERM -- "-$session_pid" 2>/dev/null || true
            sleep 2
            if ! kill -0 -- "-$session_pid" 2>/dev/null; then rm -f "$state_file"; fi
            return 1
          fi
          printf 'started session pid=%s run_id=%s\nlog=%s\n' "$session_pid" "$run_id" "$log_file"
          return 0
        fi
        sleep 1
      done
      echo 'D435i node did not become visible within 40 seconds; stop this session and inspect its run log.' >&2
      return 1
      ;;
    status)
      hardware_sensor_env
      if [[ ! -s "$state_file" ]]; then
        echo 'No hardware sensor session owned by this workspace.'
      else
        local session_pid run_dir
        readarray -t state < "$state_file"
        session_pid=${state[0]:-}
        run_dir=${state[1]:-}
        if [[ -n "$session_pid" ]] && kill -0 "$session_pid" 2>/dev/null; then
          printf 'owned session pid=%s run_dir=%s\n' "$session_pid" "$run_dir"
        else
          printf 'stale state pid=%s run_dir=%s\n' "$session_pid" "$run_dir"
        fi
      fi
      ros2 node list
      ros2 topic list -t | grep -E '^/sensors/d435i/' || true
      ;;
    stop)
      if [[ ! -s "$state_file" ]]; then
        echo 'No hardware sensor session owned by this workspace.'
        return 0
      fi
      local session_pid run_dir process_group
      readarray -t state < "$state_file"
      session_pid=${state[0]:-}
      run_dir=${state[1]:-}
      process_group=$(ps -o pgid= -p "$session_pid" 2>/dev/null | tr -d ' ')
      if [[ "$process_group" != "$session_pid" ]]; then
        echo "Refusing to signal PID $session_pid: it is not the recorded session's process-group leader." >&2
        return 1
      fi
      if ! ps -o args= -g "$session_pid" | grep -q 'uav_sensor_interface d435i.launch.py'; then
        echo "Refusing to signal process group $session_pid: expected sensor launch is not present." >&2
        return 1
      fi
      kill -TERM -- "-$session_pid"
      for _ in $(seq 1 15); do
        if ! kill -0 -- "-$session_pid" 2>/dev/null; then
          rm -f "$state_file"
          printf 'stopped owned session pid=%s run_dir=%s\n' "$session_pid" "$run_dir"
          return 0
        fi
        sleep 1
      done
      echo "Session $session_pid did not stop after SIGTERM; state retained for inspection." >&2
      return 1
      ;;
    *)
      echo 'Usage: tools/hardware.sh sensors {start|status|stop}' >&2
      return 2
      ;;
  esac
}

case "${1:-}" in
  build)
    shift
    if [[ "$(uname -m)" != aarch64 ]]; then
      echo 'Hardware builds require the Nano ARM target.' >&2
      exit 2
    fi
    [[ -r /opt/ros/foxy/setup.bash ]] || { echo 'ROS Foxy is unavailable.' >&2; exit 2; }
    command -v colcon >/dev/null || { echo 'colcon is unavailable.' >&2; exit 2; }
    source /opt/ros/foxy/setup.bash
    export HW_DEPENDENCY_PREFIX=${HW_DEPENDENCY_PREFIX:-/home/jetson/realsense_debug/vins_integration}
    prefix=$HW_DEPENDENCY_PREFIX
    export LD_LIBRARY_PATH="$prefix/ceres21/lib:$prefix/opencv42/usr/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    export CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1 UAV_HARDWARE_BUILD=1
    if [[ -e "$workspace/.runtime/hardware-session.json" || -e "$workspace/.runtime/hardware-sensors.state" || -e "$workspace/.runtime/hw04-localization.state" ]]; then
      echo 'Refusing to build or switch installs while a hardware session is recorded.' >&2
      exit 2
    fi
    build_id="hardware-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    build_session_id=$(python3 "$workspace/tools/hardware-session.py" reserve-build \
      --build-id "$build_id" --owner-pid "$$")
    release_hardware_build_reservation() {
      local result=$?
      trap - EXIT INT TERM
      if ! python3 "$workspace/tools/hardware-session.py" release-build \
          --session-id "$build_session_id"; then
        echo 'Hardware build reservation could not be released; inspect hardware session status.' >&2
        result=1
      fi
      exit "$result"
    }
    trap release_hardware_build_reservation EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    stage="$workspace/artifacts/hardware-builds/$build_id"
    build_base="$stage/build"
    install_base="$stage/install"
    mkdir -p "$stage"
    colcon build --build-base "$build_base" --install-base "$install_base" \
      --log-base "$stage/log" --executor sequential --packages-up-to \
      uav_px4_bridge uav_navigation uav_mapping uav_sensor_interface loop_fusion --cmake-args \
      -DCMAKE_BUILD_TYPE=Release '-DCMAKE_CXX_FLAGS_RELEASE=-O2 -DNDEBUG' \
      -DBUILD_TESTING=OFF -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
      "-DOpenCV_DIR=$prefix/opencv42/usr/lib/aarch64-linux-gnu/cmake/opencv4" \
      "-DCeres_DIR=$prefix/ceres21/lib/cmake/Ceres" \
      "-DCMAKE_PROJECT_INCLUDE=$prefix/opencv42_first.cmake" "$@"
    export HW_HARDWARE_INSTALL="$install_base"
    source "$install_base/local_setup.bash"
    python3 "$workspace/tools/hardware-build-manifest.py" write --root "$workspace" --install-base "$install_base"
    python3 "$workspace/tools/check_hardware_install.py"
    if [[ -e "$workspace/hardware_install" && ! -L "$workspace/hardware_install" ]]; then
      echo 'hardware_install exists and is not a symlink; preserve it and choose a reviewed activation path.' >&2
      exit 2
    fi
    next_link="$workspace/.hardware_install.next.$$.${RANDOM}"
    ln -s "$install_base" "$next_link"
    mv -Tf "$next_link" "$workspace/hardware_install"
    echo "Activated hardware install: $install_base"
    ;;
  start|status|stop)
    exec python3 "$workspace/tools/hardware-session.py" "$@"
    ;;
  perception|map|plan|ev|control|full-load)
    layer=$1
    shift
    operation=${1:-start}
    if (($#)); then shift; fi
    exec python3 "$workspace/tools/hardware-session.py" "$operation" "$layer" "$@"
    ;;
  sensors)
    sensor_operation=${2:-}
    if [[ -z "${HW_SESSION_ID:-}" ]]; then
      if [[ "$sensor_operation" == start ]]; then
        exec python3 "$workspace/tools/hardware-session.py" start sensors
      elif [[ "$sensor_operation" == stop && -e "$workspace/.runtime/hardware-session.json" ]]; then
        session_owner=$(python3 - "$workspace/.runtime/hardware-session.json" <<'PYSTATE'
import json,sys
state=json.load(open(sys.argv[1]))
print(state.get('operation','session'))
print(state.get('layer',''))
PYSTATE
)
        mapfile -t session_owner_fields <<< "$session_owner"
        if [[ "${session_owner_fields[0]:-}" != session || "${session_owner_fields[1]:-}" != sensors ]]; then
          echo 'A different hardware session owns the camera; stop it through the unified session command.' >&2
          exit 1
        fi
        exec python3 "$workspace/tools/hardware-session.py" stop sensors
      fi
    fi
    sensors_command "$sensor_operation"
    ;;
  *) echo 'Usage: tools/hardware.sh {build|start LAYER|perception|plan|ev|control|full-load|status|stop}; sensors {start|status|stop} retains its standalone interface.' >&2; exit 2 ;;
esac
