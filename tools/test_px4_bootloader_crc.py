#!/usr/bin/env python3
import struct
import unittest
from diagnostics.probe_px4_bootloader_crc import ReadOnlyBootloader, firmware_crc


class Port:
    def __init__(self, crc=123, board=50, size=2064384, revision=5):
        self.writes = []
        self.data = b''
        self.values = {1: revision, 2: board, 3: 0, 4: size}
        self.crc = crc

    def write(self, request):
        self.writes.append(request)
        value = self.values[request[1]] if request[0] == 0x22 else self.crc
        self.data = (b'' if request == b'\x21\x20' else struct.pack('<I', value)) + b'\x12\x10'
        return len(request)

    def read(self, count):
        # Fragmented replies exercise exact-read handling.
        data, self.data = self.data[:min(count, 2)], self.data[min(count, 2):]
        return data


class Tests(unittest.TestCase):
    def test_crc_matches_upstream_algorithm(self):
        # Independent bit-at-a-time form of upstream's table-based CRC.
        def reference(data):
            state = 0
            for byte in data:
                state ^= byte
                for _ in range(8):
                    state = (state >> 1) ^ (0xedb88320 if state & 1 else 0)
            return state
        self.assertEqual(reference(b'123456789'), 0x2dfd2d88)
        for image in [b'', b'abc', b'123456789', b'\x00\xff']:
            self.assertEqual(firmware_crc(image, 12), reference(image+b'\xff'*(12-len(image))))

    def test_matching_and_nonmatching_crc(self):
        image = b'abc'
        meta = dict(board_id=50, image_maxsize=2064384)
        for crc, matched in [(firmware_crc(image, 2064384), True), (123, False)]:
            port = Port(crc=crc)
            self.assertEqual(ReadOnlyBootloader(port).verify(meta, image)['matched'], matched)
            self.assertEqual(port.writes, [b'\x21\x20'] + [b'\x22'+bytes([i])+b'\x20' for i in (1,2,3,4)] + [b'\x29\x20'])

    def test_wrong_board_geometry_and_revision_stop_before_crc(self):
        for kwargs in [dict(board=9), dict(size=1024), dict(revision=2)]:
            port = Port(**kwargs)
            with self.assertRaises(ValueError):
                ReadOnlyBootloader(port).verify(dict(board_id=50, image_maxsize=2064384), b'abc')
            self.assertNotIn(b'\x29\x20', port.writes)

    def test_destructive_commands_never_reach_port(self):
        port = Port()
        for request in [b'\x23\x20', b'\x27\x04abcd\x20', b'\x30\x20']:
            with self.assertRaises(ValueError):
                ReadOnlyBootloader(port).exchange(request, 0)
        self.assertEqual(port.writes, [])


if __name__ == '__main__':
    unittest.main()
