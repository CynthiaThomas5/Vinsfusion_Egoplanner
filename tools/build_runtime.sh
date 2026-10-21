#!/usr/bin/env bash
set -Ee -o pipefail
cd /workspace
source /opt/ros/jazzy/setup.bash
JOBS=$(python3 -c 'import json; print(json.load(open("config/runtime.json"))["build_jobs"])')
export CMAKE_BUILD_PARALLEL_LEVEL="$JOBS"
case "${1:-all}" in
  ros|all)
    colcon build --base-paths src --parallel-workers 1 --cmake-args -DCMAKE_BUILD_TYPE=Release
    ;;
  px4) ;;
  *) echo 'Usage: build_runtime.sh [all|ros|px4]' >&2; exit 2 ;;
esac
if [[ "${1:-all}" != ros ]]; then
  # The bind-mounted checkout belongs to the host user, not container root.
  git config --global --add safe.directory /workspace/external/PX4-Autopilot
  git -C external/PX4-Autopilot submodule foreach --recursive 'git config --global --add safe.directory "$PWD"'
  make -C external/PX4-Autopilot px4_sitl_default PX4_MAKE_ARGS="-j$JOBS"
fi
