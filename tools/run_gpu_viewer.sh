#!/usr/bin/env bash
# X11 viewers need PRIME/GLX offload in addition to the server's EGL GPU setup.
set -Eeuo pipefail
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
VIEWER=${1:-}
if [[ $# -gt 0 ]]; then shift; fi
case "$VIEWER" in
  rviz) exec ros2 run rviz2 rviz2 "$@" ;;
  gazebo) exec gz sim -g "$@" ;;
  *) echo "Usage: $0 {rviz|gazebo} [viewer arguments...]" >&2; exit 2 ;;
esac
