#!/usr/bin/env bash
# Native ARM build; keep Agent middleware outside the Foxy runtime prefix.
set -eo pipefail
workspace=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
run="$workspace/artifacts/runs/hw07-usb-20261103-01"
prefix="$workspace/install-hardware-agent"
source /opt/ros/foxy/setup.bash
set -u
mkdir -p "$run/sources"
mkdir -p "$prefix"
touch "$prefix/COLCON_IGNORE"
python3 - "$workspace" "$run" <<'PY'
import hashlib, json, sys
from pathlib import Path
workspace, run = map(Path, sys.argv[1:])
for name, entry in json.loads((workspace / 'config/hardware/px4_dds.json').read_text())['archives'].items():
    if hashlib.sha256((run / name).read_bytes()).hexdigest() != entry['sha256']:
        raise SystemExit('Archive checksum mismatch: ' + name)
PY
if [[ ! -x "$run/cmake/cmake/data/bin/cmake" ]]; then
  python3 -m zipfile -e "$run/cmake-3.27.9-py2.py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl" "$run/cmake"
fi
chmod +x "$run/cmake/cmake/data/bin/"*
export PATH="$run/cmake/cmake/data/bin:$PATH"
[[ -d "$run/sources/Fast-CDR-2.2.0" ]] || tar -xzf "$run/fastcdr-v2.2.0.tar.gz" -C "$run/sources"
[[ -d "$run/sources/Fast-DDS-2.14.0" ]] || tar -xzf "$run/fastdds-v2.14.0.tar.gz" -C "$run/sources"
dpkg-deb -x "$run/libasio-dev_1.12.2-1_all.deb" "$run/asio"
build_install() {
  local name=$1 source_dir=$2
  shift 2
  cmake -S "$source_dir" -B "$run/build-$name" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DCMAKE_PREFIX_PATH="$prefix;/opt/ros/foxy" "$@"
  cmake --build "$run/build-$name" --parallel 2
  cmake --install "$run/build-$name"
}
build_install fastcdr "$run/sources/Fast-CDR-2.2.0" -DBUILD_TESTING=OFF
build_install fastdds "$run/sources/Fast-DDS-2.14.0" \
  -DTHIRDPARTY=OFF -DCOMPILE_TOOLS=OFF -DSECURITY=OFF -DBUILD_TESTING=OFF \
  -DSHM_TRANSPORT_DEFAULT=OFF -DAsio_INCLUDE_DIR="$run/asio/usr/include"
build_install spdlog "$workspace/src/vendor/spdlog" -DSPDLOG_BUILD_SHARED=ON
build_install agent "$workspace/src/vendor/micro_xrce_dds_agent" \
  -DUAGENT_SUPERBUILD=OFF -DUAGENT_USE_SYSTEM_FASTCDR=ON \
  -DUAGENT_USE_SYSTEM_FASTDDS=ON -DUAGENT_USE_SYSTEM_LOGGER=OFF \
  -DUAGENT_P2P_PROFILE=OFF -DUAGENT_DISCOVERY_PROFILE=OFF \
  -DUAGENT_SOCKETCAN_PROFILE=OFF -DUAGENT_SECURITY_PROFILE=OFF \
  -DUAGENT_BUILD_TESTS=OFF
