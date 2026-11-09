#!/usr/bin/env python3
"""Read-only PX4 bootloader identity/CRC; never reboots, erases or programs."""
import argparse
import binascii
import hashlib
import json
import struct
import time
import base64
import zlib
from pathlib import Path

ALLOWED = {b'\x21\x20', b'\x29\x20'} | {
    b'\x22' + bytes([info]) + b'\x20' for info in (1, 2, 3, 4)}


def load_firmware(path, expected_sha256):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Firmware SHA256 mismatch')
    meta = json.loads(raw)
    if meta.get('magic') != 'PX4FWv1' or meta['board_id'] != 50:
        raise ValueError('Expected verified FMUv5 PX4FWv1 image')
    image = zlib.decompress(base64.b64decode(meta['image']))
    if not len(image) == meta['image_size'] <= meta['image_maxsize'] == 2064384:
        raise ValueError('Unexpected image geometry')
    return meta, image


def firmware_crc(image, size):
    if not len(image) <= size or size % 4:
        raise ValueError('Invalid firmware CRC range')
    # PX4 bootloader CRC starts at zero and has no final XOR.
    padded = image + b'\xff' * (size - len(image))
    return (binascii.crc32(padded, 0xffffffff) ^ 0xffffffff) & 0xffffffff


class ReadOnlyBootloader:
    def __init__(self, port):
        self.port = port

    def exchange(self, request, count):
        if request not in ALLOWED:
            raise ValueError('Only SYNC, GET_DEVICE and GET_CRC are allowed')
        if self.port.write(request) != len(request):
            raise RuntimeError('Short bootloader request write')
        reply = bytearray()
        deadline = time.monotonic() + 3
        while len(reply) < count + 2 and time.monotonic() < deadline:
            reply.extend(self.port.read(count + 2 - len(reply)))
        if len(reply) != count + 2 or reply[-2:] != b'\x12\x10':
            raise RuntimeError('Bootloader timeout or invalid INSYNC/OK')
        return bytes(reply[:count])

    def verify(self, meta, image):
        self.exchange(b'\x21\x20', 0)
        values = [struct.unpack('<I', self.exchange(
            b'\x22' + bytes([info]) + b'\x20', 4))[0] for info in (1, 2, 3, 4)]
        revision, board, board_revision, size = values
        if not 3 <= revision <= 5:
            raise ValueError('Bootloader CRC protocol revision not reviewed')
        if board != meta['board_id'] or size != meta['image_maxsize']:
            raise ValueError('Bootloader board/flash geometry mismatch; no CRC inference')
        actual = struct.unpack('<I', self.exchange(b'\x29\x20', 4))[0]
        expected = firmware_crc(image, size)
        return dict(bootloader_revision=revision, board_id=board,
                    board_revision=board_revision, flash_bytes=size,
                    expected_crc=expected, actual_crc=actual, matched=actual == expected,
                    writes='SYNC/GET_DEVICE/GET_CRC only; no reboot/erase/program')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--firmware', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--already-in-bootloader', action='store_true',
                        help='Required state assertion; this tool cannot enter bootloader')
    args = parser.parse_args()
    if not args.already_in_bootloader:
        parser.error('Do not probe running flight stack; enter bootloader separately in approved scope')
    meta, image = load_firmware(args.firmware, args.sha256)
    import serial
    with serial.Serial(args.port, 115200, timeout=.3, write_timeout=2, exclusive=True) as port:
        result = ReadOnlyBootloader(port).verify(meta, image)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if not result['matched']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
