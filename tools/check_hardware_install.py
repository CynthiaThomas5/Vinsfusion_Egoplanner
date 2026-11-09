#!/usr/bin/env python3
"""Check that runtime modules and the native depth adapter match selected build."""
import importlib
from pathlib import Path
import os

root=Path(__file__).resolve().parents[1]
install=Path(os.environ.get('HW_HARDWARE_INSTALL',root/'install')).resolve()
count=0
for package in ('uav_sensor_interface','uav_sim','uav_localization',
                'uav_mapping','uav_navigation','uav_px4_bridge'):
 installed=Path(importlib.import_module(package).__file__).resolve().parent
 source=root/'src/own'/package/package
 for src in source.rglob('*.py'):
  relative=src.relative_to(source)
  dst=installed/relative
  if not dst.is_file() or dst.read_bytes()!=src.read_bytes():
   raise SystemExit('Installed Python source mismatch: '+str(src)+'; build and select a fresh hardware install')
  count+=1
import subprocess,sys
subprocess.run([sys.executable,str(root/'tools/hardware-build-manifest.py'),'check',
                '--root',str(root),'--install-base',str(install)],check=True)
print('Installed Python source content matches:',count)
