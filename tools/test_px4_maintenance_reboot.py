#!/usr/bin/env python3
from pathlib import Path
from types import SimpleNamespace
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'diagnostics'))
from reboot_unarmed_px4 import require_unarmed_px4

def heartbeat(armed=False,autopilot=12,system=1):
 return SimpleNamespace(autopilot=autopilot,base_mode=128 if armed else 0,get_srcSystem=lambda:system,get_srcComponent=lambda:1)
require_unarmed_px4(heartbeat())
for h in (None,heartbeat(armed=True),heartbeat(autopilot=0),heartbeat(system=2)):
 try:require_unarmed_px4(h)
 except RuntimeError:pass
 else:raise AssertionError('unsafe/unidentified reboot admitted')
print('Maintenance reboot identity/unarmed guard PASS')
