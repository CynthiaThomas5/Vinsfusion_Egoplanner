"""Read Image metadata from CDR without converting its unused pixel sequence."""
import struct
from types import SimpleNamespace


def image_metadata(serialized):
    data = memoryview(serialized)
    if len(data) < 4 or bytes(data[:2]) not in (b'\x00\x00', b'\x00\x01'):
        raise ValueError('Unsupported Image CDR encapsulation')
    endian = '<' if data[1] == 1 else '>'
    offset = 4

    def integer(signed=False):
        nonlocal offset
        offset = (offset + 3) & ~3
        if offset + 4 > len(data):
            raise ValueError('Truncated Image metadata')
        value = struct.unpack_from(endian + ('i' if signed else 'I'), data, offset)[0]
        offset += 4
        return value

    def string():
        nonlocal offset
        length = integer()
        if length < 1 or offset + length > len(data) or data[offset + length - 1] != 0:
            raise ValueError('Invalid Image CDR string')
        value = bytes(data[offset:offset + length - 1]).decode('utf-8')
        offset += length
        return value

    sec, nanosec = integer(True), integer()
    if nanosec >= 1_000_000_000:
        raise ValueError('Invalid Image timestamp')
    frame = string()
    height, width = integer(), integer()
    encoding = string()
    if offset >= len(data):
        raise ValueError('Truncated Image endianness')
    is_bigendian = data[offset]
    offset += 1
    step = integer()
    length = integer()
    if offset + length > len(data):
        raise ValueError('Truncated Image pixel sequence')
    return SimpleNamespace(
        header=SimpleNamespace(frame_id=frame, stamp=SimpleNamespace(sec=sec, nanosec=nanosec)),
        height=height, width=width, encoding=encoding, step=step,
        is_bigendian=is_bigendian, data=data[offset:offset + length])
