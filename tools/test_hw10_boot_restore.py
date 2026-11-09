#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'diagnostics'))
from hw07_usb_session import build_boot_script,BASE_SCRIPT
plain=build_boot_script(600,True,False);heading=build_boot_script(600,True,True)
assert 'sleep 600' in plain and plain.count('logger on')==1 and plain.count('logger off')==1
assert not any('EKF2_MAG' in x for x in plain)
assert heading.index('logger off')<heading.index('param set EKF2_MAG_TYPE 5')<heading.index('param set SYS_USB_AUTO 2')
assert heading.index('param set EKF2_MAG_CHECK 0')<heading.index('param save')<heading.index('mavlink start -d /dev/ttyACM0 -m onboard')
assert build_boot_script(160)==('set +e',)+BASE_SCRIPT # only add guaranteed continuation after failed commands
print('Scoped heading experiment, original defaults, logger/parameter/USB recovery ordering PASS')

# NSH background consoles start with exit-on-error; a failed diagnostic must not
# skip the recovery commands. Exercise that contract under equivalent shell flags.
import subprocess
body="""param() { return 0; }
logger() { return 1; }
uxrce_dds_client() { return 1; }
sleep() { return 0; }
mavlink() { echo USB_RECOVERED; }
rm() { echo OWNED_HOOK_REMOVED; }
"""+'\n'.join(heading)
r=subprocess.run(['bash','-e','-c',body],capture_output=True,text=True)
assert r.returncode==0 and 'USB_RECOVERED' in r.stdout and 'OWNED_HOOK_REMOVED' in r.stdout,r
print('Failed logger/DDS commands cannot skip USB/parameter recovery PASS')

# A still-running DDS client must block every step that enables USB MAVLink.
blocked=body.replace('uxrce_dds_client() { return 1; }',
                     'uxrce_dds_client() { return 0; }')
r=subprocess.run(['bash','-e','-c',blocked],capture_output=True,text=True)
assert r.returncode==1 and 'HW10_USB_RESTORE_BLOCKED_DDS_STILL_RUNNING' in r.stdout,r
assert 'USB_RECOVERED' not in r.stdout and 'OWNED_HOOK_REMOVED' not in r.stdout,r
assert heading.index('if uxrce_dds_client status')<heading.index('param set SYS_USB_AUTO 2')
print('DDS still running blocks USB MAVLink takeover and hook deletion PASS')
