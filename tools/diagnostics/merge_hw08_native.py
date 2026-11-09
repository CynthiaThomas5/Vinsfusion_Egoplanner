#!/usr/bin/env python3
"""Merge native CSV with FC wire capture, using Nano receive times for phase labels."""
import argparse
import bisect
import csv
import json
from pathlib import Path


def merge(native, board, output):
    rows = [json.loads(x) for x in board.read_text().splitlines() if x]
    phases = sorted((x['system_ns'],x['phase']) for x in rows)
    times = [x[0] for x in phases]
    with output.open('w') as target:
        for row in rows:
            target.write(json.dumps(row)+'\n')
        with native.open() as source:
            for row in csv.DictReader(source):
                if row.get('az') is None:
                    continue  # live file snapshot can have one incomplete final row
                system = int(row['system_ns'])
                index = max(0,bisect.bisect_right(times,system)-1)
                common = dict(kind=row['kind'], phase=phases[index][1],
                              system_ns=system,monotonic_ns=int(row['monotonic_ns']))
                vector = lambda keys: [float(row[k]) for k in keys]
                if row['kind'] == 'imu':
                    data=dict(stamp_ns=int(row['source_ns']),gyro=vector(('wx','wy','wz')),
                              accel=vector(('ax','ay','az')))
                elif row['kind'] == 'optimized':
                    data=dict(stamp_ns=int(row['source_ns']),p=vector(('px','py','pz')),
                              q_xyzw=vector(('qx','qy','qz','qw')),
                              v_body=vector(('vx','vy','vz')),omega_body=vector(('wx','wy','wz')))
                else:
                    raise ValueError('Unknown native record kind')
                target.write(json.dumps(dict(common,data=data))+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native',type=Path)
    parser.add_argument('board',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    merge(args.native,args.board,args.output)
