#!/usr/bin/env python3
"""Bench opt-in selects canonical approximation without qualifying the rig."""
from pathlib import Path
from types import SimpleNamespace
import json
from uav_px4_bridge.hardware_ev import HardwareEVPath
root=Path(__file__).resolve().parents[1]
class Node:
 def __init__(self,allow):self.allow=allow
 def get_parameter(self,k):return SimpleNamespace(value=self.allow if k=='allow_approximate_bench_ev' else False if k=='use_sim_time' else '')
 def create_publisher(self,*a):return SimpleNamespace(publish=lambda msg:None)
 def create_subscription(self,*a,**kw):return None
 def create_timer(self,*a,**kw):return None
 def get_logger(self):return SimpleNamespace(warning=lambda *a:None)
config=json.loads((root/'config/hardware/px4_bridge_ev.json').read_text());profile=json.loads((root/'config/hardware/px4_profile.json').read_text());frames=json.loads((root/'config/components/px4_bridge/frames_vio_closed_loop.json').read_text())
rig=root/'config/hardware/rig.json';original=rig.read_bytes()
for allow in (False,True):
 p=HardwareEVPath(Node(allow),config,profile,frames,str(rig),'ev_only')
 assert (p.matrix is not None)==allow
assert rig.read_bytes()==original
assert not json.loads(original)['airframe_mount']['control_usable']
print('Default blocked / explicit bench EV mount / canonical rig unchanged PASS')
