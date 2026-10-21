#!/usr/bin/env python3
"""Read physical IMU settling through the native CLI, without Python Gazebo bindings."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def acceleration_norms(text):
    decoder = json.JSONDecoder()
    norms = []
    while text.strip():
        message, end = decoder.raw_decode(text.lstrip())
        text = text.lstrip()[end:]
        if not isinstance(message, dict):
            raise ValueError('IMU message must be an object')
        acceleration = message.get('linearAcceleration', message.get('linear_acceleration'))
        if not isinstance(acceleration, dict):
            raise ValueError('IMU acceleration missing')
        values = [float(acceleration.get(axis, 0.0)) for axis in ('x', 'y', 'z')]
        if not all(math.isfinite(value) for value in values):
            raise ValueError('Nonfinite IMU acceleration')
        norms.append(math.sqrt(sum(value * value for value in values)))
    return norms


def settled(norms, policy):
    count = policy['min_good_samples']
    return len(norms) >= count and all(
        policy['min_accel_norm_m_s2'] < value < policy['max_accel_norm_m_s2']
        for value in norms[-count:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads((ROOT / 'config/components/simulation/imu_settle_gate.json').read_text())
    started = time.monotonic()
    norms, returncodes, error = [], [], ''
    command = ['gz', 'topic', '-e', '-t', '/sensors/d435i/imu',
               '-n', str(policy['batch_samples']), '--json-output']
    while time.monotonic() - started < policy['timeout_wall_s']:
        remaining = policy['timeout_wall_s'] - (time.monotonic() - started)
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=remaining)
            returncodes.append(result.returncode)
            if result.returncode:
                error = 'gz_cli_failed: ' + result.stderr[-2000:]
                break
            norms.extend(acceleration_norms(result.stdout))
            if settled(norms, policy):
                break
        except (subprocess.TimeoutExpired, ValueError) as exc:
            error = str(exc)
            break
    ready = not error and settled(norms, policy)
    args.output.write_text(json.dumps({
        'scope': __doc__, 'ready': ready, 'samples': len(norms),
        'latest_norm': norms[-1] if norms else None,
        'wall_s': time.monotonic() - started,
        'gz_cli_returncodes': returncodes, 'error': error,
    }, indent=2) + '\n')
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
