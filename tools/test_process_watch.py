#!/usr/bin/env python3
"""Read-only process identity checks used by active-task fault handling."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_px4_bridge'))

from uav_px4_bridge.process_watch import (  # noqa: E402
    find_process_identities,
    process_identity_is_running,
)


def write_process(proc_root, pid, executable, start_time_ticks):
    entry = Path(proc_root) / str(pid)
    entry.mkdir()
    (entry / 'cmdline').write_bytes(
        f'/opt/ros/lib/ego_planner/{executable}\0--ros-args\0'.encode())
    tail = ['S'] + ['0'] * 18 + [str(start_time_ticks)]
    (entry / 'stat').write_text(f'{pid} (ego node with spaces) ' + ' '.join(tail))
    return entry


class ProcessWatchTests(unittest.TestCase):
    def test_finds_exact_executable_basename_and_verifies_start_time(self):
        with tempfile.TemporaryDirectory() as proc_root:
            entry = write_process(proc_root, 212, 'ego_planner_node', 918)
            write_process(proc_root, 213, 'ego_planner_node_helper', 919)
            identities = find_process_identities('ego_planner_node', proc_root)
            self.assertEqual(len(identities), 1)
            self.assertEqual(identities[0].pid, 212)
            self.assertTrue(process_identity_is_running(identities[0], proc_root))

            (entry / 'stat').write_text(
                '212 (ego node with spaces) ' + ' '.join(['S'] + ['0'] * 18 + ['920']))
            self.assertFalse(process_identity_is_running(identities[0], proc_root))

    def test_rejects_path_in_executable_configuration(self):
        with self.assertRaises(ValueError):
            find_process_identities('/usr/bin/ego_planner_node', '/no-such-proc')

    def test_missing_proc_identity_is_not_running(self):
        from uav_px4_bridge.process_watch import ProcessIdentity
        with tempfile.TemporaryDirectory() as proc_root:
            self.assertFalse(process_identity_is_running(
                ProcessIdentity(999, 1), proc_root))


if __name__ == '__main__':
    unittest.main()
