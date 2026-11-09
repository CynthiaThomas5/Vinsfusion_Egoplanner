#!/usr/bin/env python3
"""Workstation tests for framed relay timing and fragmented MAVLink traffic."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent/'diagnostics'))
from relay_hw08_serial import HEADER
from decode_hw08_serial import read_exact


class RelayTests(unittest.TestCase):
    def test_truncated_frame_is_not_silently_accepted(self):
        self.assertIsNone(read_exact(io.BytesIO(), 3))
        with self.assertRaises(EOFError):
            read_exact(io.BytesIO(b'ab'), 3)

    def test_fragmented_wire_and_nano_clock_midpoint(self):
        os.environ['MAVLINK20'] = '1'
        from pymavlink.dialects.v20 import common
        mav = common.MAVLink(None, srcSystem=1, srcComponent=1)
        epoch, mono, fc = 1792380000000000000, 1000000000, 123000000000
        wire = mav.timesync_encode(fc, epoch).pack(mav)
        framed = HEADER.pack(2, epoch, mono, 0)
        for payload in (wire[:5], wire[5:]):
            framed += HEADER.pack(1, epoch+2000000, mono+2000000, len(payload))+payload
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable,
                str(Path(__file__).parent/'diagnostics/decode_hw08_serial.py'),
                '--output', directory], input=framed, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [json.loads(x) for x in (Path(directory)/'board.jsonl').read_text().splitlines()]
        pair = next(x for x in rows if x['kind'] == 'timesync_pair')
        self.assertEqual(pair['system_ns'], epoch+2000000)
        self.assertEqual(pair['data']['rtt_ns'], 2000000)
        self.assertEqual(pair['data']['host_minus_fc_ns'], epoch+1000000-fc)


if __name__ == '__main__':
    unittest.main()
