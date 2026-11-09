#!/usr/bin/env python3
"""Forward Nano RX bytes to local QGC. UDP replies are never sent to the vehicle."""
import argparse
import shlex
import socket
import subprocess
from decode_hw08_serial import read_exact
from relay_hw08_serial import HEADER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--device', default='/dev/ttyACM0')
    args = parser.parse_args()
    command = ('cd ' + shlex.quote(args.root) + '; '
               'PYTHONPATH="$PWD/artifacts/runs/hw07-usb-20261103-01/python" '
               'exec python3 tools/diagnostics/relay_hw08_serial.py --device '
               + shlex.quote(args.device) + ' --seconds 86400 --discovery-heartbeat')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        with subprocess.Popen(['ssh', '-o', 'BatchMode=yes', args.host, command],
                              stdout=subprocess.PIPE) as child:
            try:
                while True:
                    header = read_exact(child.stdout, HEADER.size)
                    if header is None:
                        break
                    kind, _, _, size = HEADER.unpack(header)
                    if kind not in (1, 2) or size > 8192 or (kind == 2 and size):
                        raise ValueError('Invalid RX relay framing')
                    payload = read_exact(child.stdout, size) if size else b''
                    if kind == 1 and payload:
                        udp.sendto(payload, ('127.0.0.1', 14550))
            except KeyboardInterrupt:
                pass
            finally:
                child.terminate()
            try:
                code = child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                code = child.wait()
            if code not in (0, -15, 255):
                raise SystemExit(code)


if __name__ == '__main__':
    main()
