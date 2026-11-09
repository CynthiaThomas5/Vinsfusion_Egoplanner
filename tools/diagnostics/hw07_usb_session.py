#!/usr/bin/env python3
"""Fixed HW07 USB diagnostics and a one-shot boot DDS transport session.

Only SYS_USB_AUTO changes, backed up and restored. No EV, mode or arming commands.
After an operator power cycle the FC restores USB MAVLink without the host.
"""
import argparse
import json
import os
import struct
import time
from pathlib import Path

os.environ['MAVLINK20'] = '1'
os.environ['MAVLINK_DIALECT'] = 'common'
from probe_hw07_px4 import shell_command_complete

SCRIPT = (
    'if param compare -s SYS_USB_AUTO 0',
    'then',
    'sleep 8',
    'echo HW07_BOOT_DDS_BEGIN',
    'uxrce_dds_client start -t serial -d /dev/ttyACM0 -b 921600',
    'sleep 160',
    'uxrce_dds_client status',
    'uxrce_dds_client stop',
    'if uxrce_dds_client status',
    'then',
    'echo HW10_USB_RESTORE_BLOCKED_DDS_STILL_RUNNING',
    'exit 1',
    'fi',
    'param set SYS_USB_AUTO 2',
    'param save',
    'mavlink start -d /dev/ttyACM0 -m onboard',
    'fi',
    'rm /fs/microsd/etc/extras.txt',
)
SCRIPT_PATH = '/fs/microsd/hw07-boot-dds.sh'
HOOK = 'sh ' + SCRIPT_PATH + ' > /fs/microsd/hw07-boot-dds.log &'


BASE_SCRIPT=SCRIPT

def build_boot_script(seconds,unarmed_log=False,heading_init=False):
    lines=['set +e']
    for line in BASE_SCRIPT:
        if line=='sleep 160':line='sleep '+str(seconds)
        if line=='param set SYS_USB_AUTO 2':
            if unarmed_log:lines.append('logger off')
            if heading_init:lines.extend(('param set EKF2_MAG_TYPE 5','param set EKF2_MAG_CHECK 0'))
        lines.append(line)
        if unarmed_log and line=='sleep 8':lines.append('logger on')
    return tuple(lines)


def main():
    from pymavlink import mavutil, mavftp
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare-boot', 'verify'))
    parser.add_argument('--device', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--session-label', default='hw07')
    parser.add_argument('--dds-seconds', type=int, default=160)
    parser.add_argument('--unarmed-log', action='store_true')
    parser.add_argument('--heading-reference-init', action='store_true', help='Temporary MAG_TYPE6/CHECK3; requires original5/0 and restores both')
    args = parser.parse_args()
    if not args.session_label.isalnum() or not 60 <= args.dds_seconds <= 900:
        raise ValueError('Session label must be alphanumeric and DDS window 60..900 seconds')
    global SCRIPT, SCRIPT_PATH, HOOK
    SCRIPT = build_boot_script(args.dds_seconds,args.unarmed_log,args.heading_reference_init)
    SCRIPT_PATH = SCRIPT_PATH.replace('hw07-', args.session_label + '-')
    HOOK = HOOK.replace('hw07-', args.session_label + '-')
    args.output.mkdir(parents=True, exist_ok=True)
    link = mavutil.mavlink_connection(args.device, baud=115200, source_system=245, source_component=190)
    heartbeat = link.wait_heartbeat(timeout=10)
    if heartbeat is None or heartbeat.autopilot != 12 or heartbeat.base_mode & 128:
        link.close()
        raise RuntimeError('Expected actual disarmed PX4 heartbeat')
    log = (args.output / (args.action + '-shell.txt')).open('w', buffering=1)
    log.write(json.dumps(heartbeat.to_dict()) + '\n')

    def command(text, seconds=4):
        text = text.replace('hw07-', args.session_label + '-')
        log.write('\nCOMMAND ' + text + '\n')
        data = (text + '\n').encode()
        for offset in range(0, len(data), 70):
            chunk = data[offset:offset + 70]
            link.mav.serial_control_send(10, 6, 0, 0, len(chunk), list(chunk) + [0] * (70 - len(chunk)))
        deadline = time.monotonic() + seconds
        result = ''
        while time.monotonic() < deadline:
            msg = link.recv_match(type='SERIAL_CONTROL', blocking=True, timeout=.1)
            if msg:
                result += bytes(msg.data[:msg.count]).decode(errors='replace')
                if shell_command_complete(result, text):
                    break
        log.write(result)
        print(text, repr(result), flush=True)
        if not shell_command_complete(result, text):
            raise RuntimeError('NSH command did not complete: ' + text)
        return result

    try:
        if args.action == 'prepare-boot':
            existing = command('ls -l /fs/microsd/etc/extras.txt')
            if not any(error in existing for error in ('No such file', 'Not a directory')):
                raise RuntimeError('Refusing to overwrite existing SD startup hook')
            original = command('param show SYS_USB_AUTO')
            if ': 2' not in original:
                raise RuntimeError('Expected original SYS_USB_AUTO=2')
            for name in ('UXRCE_DDS_DOM_ID', 'UXRCE_DDS_SYNCT', 'UXRCE_DDS_SYNCC'):
                command('param show -q ' + name)
            command('param save /fs/microsd/hw07-before.params')
            saved = command('ls -l /fs/microsd/hw07-before.params')
            if 'No such file' in saved or 'failed' in saved:
                raise RuntimeError('Native parameter backup not created')
            mode = command('param show USB_MAV_MODE')
            if ': 2' not in mode:
                raise RuntimeError('Restore script expects original USB_MAV_MODE=2')
            for index, line in enumerate(SCRIPT):
                command('echo "' + line + '" ' + ('>' if index == 0 else '>>') + ' ' + SCRIPT_PATH)
            result = command('cat ' + SCRIPT_PATH)
            if not all(line in result for line in SCRIPT):
                raise RuntimeError('FC-side recovery script readback mismatch')
            command('mkdir -p /fs/microsd/etc')
            command('echo "' + HOOK + '" > /fs/microsd/etc/extras.txt')
            if HOOK not in command('cat /fs/microsd/etc/extras.txt'):
                raise RuntimeError('Startup hook readback mismatch')
            if args.heading_reference_init:
                if ': 5' not in command('param show EKF2_MAG_TYPE') or ': 0' not in command('param show EKF2_MAG_CHECK'):
                    raise RuntimeError('Heading reference experiment requires original MAG_TYPE5/CHECK0')
                command('param set EKF2_MAG_TYPE 6')
                command('param set EKF2_MAG_CHECK 3')
            command('param set SYS_USB_AUTO 0')
            command('param save')
            if ': 0' not in command('param show SYS_USB_AUTO'):
                raise RuntimeError('USB communication preparation failed')
        else:
            command('param save /fs/microsd/hw07-after.params')
            for text in ('cat /fs/microsd/hw07-boot-dds.log', 'ls -l /fs/microsd/etc/extras.txt',
                         'uxrce_dds_client status',
                         'mavlink status', 'param show SYS_USB_AUTO', 'param show USB_MAV_MODE',
                         'param show UXRCE_DDS*', 'param show -q UXRCE_DDS_DOM_ID',
                         'param show -q UXRCE_DDS_SYNCT', 'param show -q UXRCE_DDS_SYNCC'):
                command(text, 4)
        if args.action in ('prepare-boot', 'verify'):
            phase = 'before' if args.action == 'prepare-boot' else 'after'
            target = args.output / ('native-' + phase + '.bson')
            ftp = mavftp.MAVFTP(link, heartbeat.get_srcSystem(), heartbeat.get_srcComponent())
            ftp.cmd_get(['/fs/microsd/' + args.session_label + '-' + phase + '.params', str(target)])
            result = ftp.process_ftp_reply('OpenFileRO', timeout=20)
            if result.error_code != mavftp.FtpError.Success:
                raise RuntimeError('Native backup download failed: ' + str(result.error_code))
            data = target.read_bytes()
            if len(data) < 5 or struct.unpack_from('<i', data)[0] != len(data) or data[-1] != 0:
                raise RuntimeError('Native backup BSON envelope invalid')
            log.write('\nDownloaded native BSON: ' + str(len(data)) + ' bytes\n')
    finally:
        link.mav.serial_control_send(10, 0, 0, 0, 0, [0] * 70)
        link.close()
        log.close()


if __name__ == '__main__':
    main()
