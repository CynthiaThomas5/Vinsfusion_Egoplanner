#!/usr/bin/env python3
"""Compare existing 1 Hz VINS pose log with read-only FC quaternion capture.

Uses the declared nominal optical-to-FRD mount. One constant world yaw is
estimated from the initial static samples; it is frozen for every later phase.
This is a consistency check, not external position ground truth or calibration.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def rotation(q):
    q = np.asarray(q, dtype=float)
    q /= np.linalg.norm(q)
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def analyze(board, localization):
    rows = [json.loads(x) for x in board.read_text().splitlines() if x]
    clocks = [x['data'] for x in rows if x['kind'] == 'timesync_pair'
              and x['data']['rtt_ns'] <= 10000000]
    fc = [x for x in rows if x['kind'] == 'mavlink'
          and x['data']['mavpackettype'] == 'ATTITUDE_QUATERNION']
    if len(clocks) < 2 or not fc:
        raise ValueError('Need actual clocks and FC attitude')
    clocks.sort(key=lambda x: x['fc_hrt_ns'])
    origin = clocks[0]['host_midpoint_system_ns']
    hrt0 = clocks[0]['fc_hrt_ns']
    fc_hrt = np.array([x['data']['time_boot_ms']*1000000-hrt0 for x in fc], dtype=float)
    fc_t = np.interp(fc_hrt,
        [x['fc_hrt_ns']-hrt0 for x in clocks],
        [x['host_midpoint_system_ns']-origin for x in clocks])
    poses, seen, states = [], set(), {}
    for line in localization.read_text().splitlines():
        if 'localization_age_observation ' not in line:
            continue
        data = json.loads(line.split('localization_age_observation ', 1)[1])
        reason = data['status']['reason']
        states[reason] = states.get(reason, 0)+1
        pose = data['pose_observation']
        if not data['status']['valid'] or not pose or pose['stamp_ns'] in seen:
            continue
        seen.add(pose['stamp_ns'])
        stamp = pose['stamp_ns']-origin
        if stamp < fc_t[0] or stamp > fc_t[-1]:
            continue
        index = int(np.argmin(abs(fc_t-stamp)))
        if abs(fc_t[index]-stamp) > 20000000:
            continue
        message = fc[index]['data']
        r_fc = rotation([message['q2'],message['q3'],message['q4'],message['q1']])
        r_wi = rotation(pose['orientation_xyzw'])
        r_bi = np.array([[0,0,1],[1,0,0],[0,1,0]])
        # ENU-like gravity-up arbitrary world -> down world. No North claim.
        r_local = np.array([[0,1,0],[1,0,0],[0,0,-1]]) @ r_wi @ r_bi.T
        poses.append((fc[index]['phase'], pose, r_fc, r_local))
    baseline = [x for x in poses if x[0] == 'baseline'][:10]
    if len(baseline) < 3:
        raise ValueError('Need at least 3 valid baseline pose pairs')
    angles = [np.arctan2((a @ b.T)[1,0], (a @ b.T)[0,0]) for _,_,a,b in baseline]
    yaw = np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))
    c, s = np.cos(yaw), np.sin(yaw)
    align = np.array([[c,-s,0],[s,c,0],[0,0,1]])
    result = dict(valid_pose_pairs=len(poses), status_reason_counts=states,
                  frozen_world_yaw_deg=float(np.degrees(yaw)), phases={})
    for phase in sorted(set(x[0] for x in poses)):
        selected = [x for x in poses if x[0] == phase]
        errors = [np.degrees(np.arccos(np.clip((np.trace(a @ (align @ b).T)-1)/2,-1,1)))
                  for _,_,a,b in selected]
        positions = np.array([x[1]['position_m'] for x in selected])
        result['phases'][phase] = dict(samples=len(selected),
            full_attitude_error_median_deg=float(np.median(errors)),
            full_attitude_error_max_deg=float(max(errors)),
            imu_position_range_m=np.ptp(positions,axis=0).tolist())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('board', type=Path)
    parser.add_argument('localization', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.board,args.localization), indent=2))
