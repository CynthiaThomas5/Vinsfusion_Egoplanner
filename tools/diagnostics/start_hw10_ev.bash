#!/usr/bin/env bash
# User-authorized disarmed bench EV only; no mode/arming/control publisher.
set -eo pipefail
cd "$(dirname "$0")/../.."
run=${1:-$PWD/artifacts/runs/hw10-20261104-01}
mkdir -p "$run"
[[ ! -e "$run/ev.pid" ]] || { echo 'Inspect existing HW10 PID state first'; exit 1; }
setsid env LD_LIBRARY_PATH="$PWD/install-hardware-agent/lib" "$PWD/install-hardware-agent/bin/MicroXRCEAgent" serial --dev /dev/serial/by-id/usb-3D_Robotics_PX4_FMU_v5.x_0-if00 -b 921600 -v 2 > "$run/agent.log" 2>&1 < /dev/null &
echo $! > "$run/agent.pid"
source tools/hardware-env.bash
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/hardware/vins_fastdds_udp_rxbuf4m.xml
setsid ros2 run uav_px4_bridge px4_bridge --ros-args -p profile_path:="$PWD/config/hardware/px4_profile.json" -p bridge_config_path:="$PWD/config/hardware/px4_bridge_ev.json" -p frame_contract_path:="$PWD/config/components/px4_bridge/frames_vio_closed_loop.json" -p rig_config:="$PWD/config/hardware/rig.json" -p allow_approximate_bench_ev:=true -p use_sim_time:=false > "$run/ev.log" 2>&1 < /dev/null &
echo $! > "$run/ev.pid"
setsid python3 tools/diagnostics/record_hw10_ev.py --output "$run" > "$run/observer.log" 2>&1 < /dev/null &
echo $! > "$run/observer.pid"
