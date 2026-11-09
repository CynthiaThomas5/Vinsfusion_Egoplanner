#!/usr/bin/env python3
"""Exercise fresh hardware install activation with a fake colcon driver."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOLS=('hardware.sh','hardware-session.py','hardware_profile.py',
       'hardware-build-manifest.py','check_hardware_install.py')
PACKAGES=('uav_sensor_interface','uav_sim','uav_localization',
          'uav_mapping','uav_navigation','uav_px4_bridge')


class HardwareBuildTests(unittest.TestCase):
    def make_fixture(self,root):
        tools=root/'tools';tools.mkdir(parents=True)
        for name in TOOLS:
            source=ROOT/'tools'/name
            target=tools/name
            if name=='hardware.sh':
                text=source.read_text().replace(
                    '/opt/ros/foxy/setup.bash',str(root/'ros/foxy/setup.bash'))
                target.write_text(text)
            else:
                shutil.copy2(source,target)
        ros_setup=root/'ros/foxy/setup.bash'
        ros_setup.parent.mkdir(parents=True);ros_setup.write_text('')
        for package in PACKAGES:
            source=root/'src/own'/package
            module=source/package
            module.mkdir(parents=True,exist_ok=True)
            (module/'__init__.py').write_text('# fixture '+package+'\n')
            (source/'package.xml').write_text('<package>'+package+'</package>\n')
        for package,relative,content in (
                ('uav_sensor_interface','launch/d435i.launch.py','sensor-launch'),
                ('uav_sensor_interface','config/d435i_camera.yaml','sensor-config'),
                ('uav_navigation','launch/navigation.launch.py','navigation-launch')):
            target=root/'src/own'/package/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(content)
        fakebin=root/'fakebin';fakebin.mkdir()
        self.write_executable(fakebin/'uname','#!/bin/sh\nprintf "aarch64\\n"\n')
        colcon='''#!/usr/bin/env python3
import os, shutil, sys
from pathlib import Path
code=int(os.environ.get('FAKE_COLCON_EXIT','0'))
if code:
    raise SystemExit(code)
args=sys.argv[1:]
install=Path(args[args.index('--install-base')+1])
root=Path(os.environ['FAKE_PROJECT_ROOT'])
install.mkdir(parents=True)
python=install/'python'; python.mkdir()
setup='export PYTHONPATH="'+str(python)+'${PYTHONPATH:+:$PYTHONPATH}"\\n'
(install/'setup.bash').write_text(setup)
(install/'local_setup.bash').write_text(setup)
for package in ('uav_sensor_interface','uav_sim','uav_localization',
                'uav_mapping','uav_navigation','uav_px4_bridge'):
    source=root/'src/own'/package
    shutil.copytree(source/package,python/package)
    share=install/'share'/package
    share.mkdir(parents=True)
    shutil.copy2(source/'package.xml',share/'package.xml')
    for category in ('launch','config'):
        source_dir=source/category
        if source_dir.is_dir():
            shutil.copytree(source_dir,share/category,
                            ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
if os.environ.get('FAKE_BAD_INSTALL')=='1':
    (install/'share/uav_sensor_interface/launch/d435i.launch.py').write_text('stale launch')
binary=install/'uav_sensor_interface/lib/uav_sensor_interface/d435i_depth_to_meters_cpp'
binary.parent.mkdir(parents=True)
binary.write_bytes(b'fixture native binary')
'''
        self.write_executable(fakebin/'colcon',colcon)
        old=root/'old-install';old.mkdir()
        (old/'preserve-me').write_text('old active install')
        (root/'hardware_install').symlink_to(old,target_is_directory=True)
        return fakebin,old

    @staticmethod
    def write_executable(path,content):
        path.write_text(content)
        path.chmod(0o755)

    def run_build(self,root,fakebin,exit_code=0,bad_install=False):
        env=dict(os.environ,PATH=str(fakebin)+os.pathsep+os.environ.get('PATH',''),
                 FAKE_PROJECT_ROOT=str(root),FAKE_COLCON_EXIT=str(exit_code),
                 FAKE_BAD_INSTALL='1' if bad_install else '0')
        return subprocess.run(['bash','tools/hardware.sh','build'],cwd=root,env=env,
                              text=True,capture_output=True,timeout=60)

    def test_failed_build_leaves_existing_install_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fakebin,old=self.make_fixture(root)
            result=self.run_build(root,fakebin,exit_code=17)
            self.assertEqual(result.returncode,17,result.stderr)
            self.assertTrue((root/'hardware_install').is_symlink())
            self.assertEqual((root/'hardware_install').resolve(),old.resolve())
            self.assertEqual((old/'preserve-me').read_text(),'old active install')
            self.assertFalse((root/'.runtime/hardware-session.json').exists())

    def test_installed_source_mismatch_does_not_activate_new_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fakebin,old=self.make_fixture(root)
            result=self.run_build(root,fakebin,bad_install=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('launch/config/package files differ',result.stderr)
            self.assertEqual((root/'hardware_install').resolve(),old.resolve())
            self.assertTrue((old/'preserve-me').is_file())
            self.assertFalse((root/'.runtime/hardware-session.json').exists())

    def test_source_change_after_install_invalidates_saved_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fakebin,_=self.make_fixture(root)
            result=self.run_build(root,fakebin)
            self.assertEqual(result.returncode,0,result.stderr+'\n'+result.stdout)
            install=(root/'hardware_install').resolve()
            source=root/'src/own/uav_navigation/uav_navigation/__init__.py'
            source.write_text('# changed after the verified install\n')
            check=subprocess.run(
                [sys.executable,'tools/hardware-build-manifest.py','check',
                 '--root',str(root),'--install-base',str(install)],
                cwd=root,text=True,capture_output=True,timeout=30)
            self.assertNotEqual(check.returncode,0)
            self.assertIn('Hardware install identity mismatch',check.stderr)

    def test_successful_build_activates_verified_fresh_prefix_and_keeps_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fakebin,old=self.make_fixture(root)
            result=self.run_build(root,fakebin)
            self.assertEqual(result.returncode,0,result.stderr+'\n'+result.stdout)
            active=(root/'hardware_install').resolve()
            self.assertNotEqual(active,old.resolve())
            self.assertTrue((active/'.hardware-build.json').is_file())
            self.assertTrue((active/'share/uav_sensor_interface/launch/d435i.launch.py').is_file())
            self.assertTrue((active/'uav_sensor_interface/lib/uav_sensor_interface/'
                             'd435i_depth_to_meters_cpp').is_file())
            self.assertTrue((old/'preserve-me').is_file())
            self.assertFalse((root/'.runtime/hardware-session.json').exists())


if __name__=='__main__':
    unittest.main()
