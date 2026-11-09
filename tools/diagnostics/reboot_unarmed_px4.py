#!/usr/bin/env python3
"""One maintenance reboot of an identified, unarmed PX4; never arms or changes modes."""
import argparse
import json
import os
from pathlib import Path
import time


def require_unarmed_px4(heartbeat):
    if (heartbeat is None or heartbeat.autopilot!=12 or heartbeat.base_mode & 128
            or heartbeat.get_srcSystem()!=1 or heartbeat.get_srcComponent()!=1):
        raise RuntimeError('Fresh unarmed PX4 system1/component1 heartbeat required')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();os.environ['MAVLINK20']='1'
    from pymavlink import mavutil
    link=mavutil.mavlink_connection(args.device,baud=115200,source_system=245,source_component=190)
    report={'requested_wall_s':time.time()}
    try:
        heartbeat=link.wait_heartbeat(timeout=10);require_unarmed_px4(heartbeat)
        report['heartbeat']=heartbeat.to_dict()
        command=mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN
        link.mav.command_long_send(1,1,command,0,1,0,0,0,0,0,0)
        deadline=time.monotonic()+3;report['ack']=None
        while time.monotonic()<deadline:
            ack=link.recv_match(type='COMMAND_ACK',blocking=True,timeout=.1)
            if ack and ack.command==command:
                report['ack']=ack.to_dict()
                if ack.result!=mavutil.mavlink.MAV_RESULT_ACCEPTED:raise RuntimeError('Maintenance reboot denied')
                break
    finally:
        link.close();args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
