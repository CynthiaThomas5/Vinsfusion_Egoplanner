#!/usr/bin/env python3
"""Forward timestamped RX bytes; transmit only a 1 Hz MAVLink TIMESYNC query.

Run through SSH stdout. No MAVLink receive decoding, ROS participant, parameter
writes or control commands. Framing is <kind:u8, system:u64, monotonic:u64, n:u32>
followed by n bytes. Kind 1 is RX; kind 2 is a query send event (no payload).
"""
import argparse
import os
import struct
import sys
import time

HEADER = struct.Struct('<BQQI')


def main():
    os.environ['MAVLINK20'] = '1'
    from pymavlink.dialects.v20 import common
    import serial
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True)
    parser.add_argument('--seconds', type=float, default=1800.)
    parser.add_argument('--discovery-heartbeat', action='store_true', help='Send a GCS heartbeat to let USB autoconfiguration discover MAVLink; no control commands')
    args = parser.parse_args()
    output = sys.stdout.buffer
    with serial.Serial(args.device, 115200, timeout=.02, write_timeout=2.) as port:
        mav = common.MAVLink(port, srcSystem=245, srcComponent=190)
        start, next_query = time.monotonic(), 0.
        while time.monotonic()-start < args.seconds:
            if time.monotonic() >= next_query:
                system, mono = time.time_ns(), time.monotonic_ns()
                output.write(HEADER.pack(2, system, mono, 0))
                if args.discovery_heartbeat:
                    mav.heartbeat_send(common.MAV_TYPE_GCS, common.MAV_AUTOPILOT_INVALID, 0, 0, common.MAV_STATE_ACTIVE)
                mav.timesync_send(0, system)
                next_query = time.monotonic()+1.
            data = port.read(max(1, min(port.in_waiting, 8192)))
            if data:
                output.write(HEADER.pack(1, time.time_ns(), time.monotonic_ns(), len(data)))
                output.write(data)
            output.flush()


if __name__ == '__main__':
    main()
