#!/usr/bin/env python3
"""Offline reconciliation of an N07 ROS graph report with delayed DDS names."""
import argparse
import json
from pathlib import Path

from n07_ros_graph_evidence import qualify_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='original ros-graph-audit.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding='utf-8'))
    result = qualify_report(source)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'raw_capture_checks_passed': result['raw_capture_checks_passed'],
        'checks_passed': result['checks_passed'],
        'airborne_snapshot_captured': result.get('airborne_snapshot_captured'),
        'snapshot_count': len(result.get('snapshots', [])),
        'reconciliation': result['control_owner_reconciliation'],
    }, indent=2, sort_keys=True))
    if not result['checks_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
