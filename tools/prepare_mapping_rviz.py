#!/usr/bin/env python3
"""Bind the mapping RViz preset to a VINS session without starting ROS nodes."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--loop', action='store_true', help='Separate loop-map observer preset')
    args = parser.parse_args()
    epoch = json.loads(args.session.read_text())['epoch']
    if not isinstance(epoch, str) or not epoch or not epoch.isalnum():
        raise ValueError('Expected an alphanumeric VINS session epoch')
    root = Path(__file__).resolve().parents[1]
    planner = json.loads((root / 'config/components/mapping/ego_planner.json').read_text())
    preset = root / ('config/rviz/loop_observer.rviz' if args.loop else 'config/rviz/mapping.rviz')
    args.output.write_text(preset.read_text().replace(
        '__ODOM_FRAME__', f'odom_{epoch}').replace('__DRONE_ID__', str(planner['drone_id'])).replace(
        '__LOOP_FRAME__', f'loop_{epoch}_map').replace('__LOOP_NAMESPACE__', f'/loop_observer/s_{epoch}'))


if __name__ == '__main__':
    main()
