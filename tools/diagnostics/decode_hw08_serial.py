#!/usr/bin/env python3
"""Decode the Nano relay's framed stdin on the workstation, preserving Nano time."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
from relay_hw08_serial import HEADER
from record_hw08_board import timesync_pair


def read_exact(stream, length):
    data = bytearray()
    while len(data) < length:
        chunk = stream.read(length-len(data))
        if not chunk:
            if not data:
                return None
            raise EOFError('Truncated relay frame')
        data.extend(chunk)
    return bytes(data)


def main():
    os.environ['MAVLINK20'] = '1'
    from pymavlink.dialects.v20 import common
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    decoder = common.MAVLink(None)
    decoder.robust_parsing = True
    pending, counts = {}, Counter()
    stream = sys.stdin.buffer
    with (args.output/'board.jsonl').open('w', buffering=1) as output:
        while True:
            header = read_exact(stream, HEADER.size)
            if header is None:
                break
            kind, system, mono, length = HEADER.unpack(header)
            if length > 8192 or kind not in (1, 2) or (kind == 2 and length):
                raise ValueError('Invalid relay frame')
            payload = read_exact(stream, length) if length else b''
            if payload is None:
                raise EOFError('Missing relay payload')
            phase_path = args.output/'phase.txt'
            phase = phase_path.read_text().strip() if phase_path.exists() else 'baseline'
            def record(kind, data):
                output.write(json.dumps(dict(kind=kind, phase=phase, system_ns=system,
                                             monotonic_ns=mono, data=data))+'\n')
                counts[kind] += 1
            if kind == 2:
                pending = {k:v for k,v in pending.items() if mono-v[1] < 5_000_000_000}
                pending[system] = (system, mono)
                continue
            for message in decoder.parse_buffer(payload) or []:
                if message.get_srcSystem() != 1 or message.get_srcComponent() != 1:
                    continue
                name = message.get_type()
                if name in ('HEARTBEAT', 'ATTITUDE_QUATERNION', 'HIGHRES_IMU',
                            'TIMESYNC', 'STATUSTEXT'):
                    record('mavlink', message.to_dict())
                if name == 'HEARTBEAT' and message.base_mode & 128:
                    raise RuntimeError('Unexpected armed state')
                if name == 'TIMESYNC' and message.tc1 > 0 and message.ts1 in pending:
                    sent_system, sent_mono = pending.pop(message.ts1)
                    record('timesync_pair', timesync_pair(sent_system, sent_mono, mono, message.tc1))
            (args.output/'relay-summary.json').write_text(json.dumps(dict(
                counts=counts, last_system_ns=system, last_monotonic_ns=mono))+'\n')


if __name__ == '__main__':
    main()
