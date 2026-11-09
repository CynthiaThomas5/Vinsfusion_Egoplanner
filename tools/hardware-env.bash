#!/usr/bin/env bash
# Source in a clean shell to load the Nano Foxy build and its pinned libraries.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo 'Source this file: source tools/hardware-env.bash' >&2
  exit 2
fi
workspace=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export HW_DEPENDENCY_PREFIX=${HW_DEPENDENCY_PREFIX:-/home/jetson/realsense_debug/vins_integration}
prefix=$HW_DEPENDENCY_PREFIX
source /opt/ros/foxy/setup.bash || return
export LD_LIBRARY_PATH="$prefix/ceres21/lib:$prefix/opencv42/usr/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HW_HARDWARE_INSTALL=${HW_HARDWARE_INSTALL:-$(python3 "$workspace/tools/hardware_profile.py" --install-base)}
source "$HW_HARDWARE_INSTALL/setup.bash" || return
if [[ -n "${HW_SESSION_ID:-}" ]]; then
  python3 "$workspace/tools/hardware_profile.py" --session-preflighted "$HW_SESSION_ID" || return 2
else
  python3 "$workspace/tools/check_hardware_install.py" || return 2
fi
