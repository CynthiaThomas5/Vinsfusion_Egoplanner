#!/usr/bin/env python3
"""Canonical layer-to-profile and physical identity mapping checks."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import importlib.util

from hardware_profile import (read_device_identity, resolve_depth_output_profile,
                              match_observed_device_identity,hardware_config_hashes)

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    'hardware_build_manifest',ROOT/'tools/hardware-build-manifest.py')
build_manifest=importlib.util.module_from_spec(spec);spec.loader.exec_module(build_manifest)


class HardwareProfileTests(unittest.TestCase):
    def test_layer_rates_come_from_the_intended_profiles(self):
        expected={'sensors':('sensor_runtime.json',3.0),
                  'perception':('sensor_runtime.json',3.0),
                  'map':('mapping.json',5.0),
                  'plan':('planner.json',3.0),
                  'ev':('planner.json',3.0),
                  'control':('planner.json',3.0),
                  'full-load':('planner.json',3.0)}
        for layer,(filename,rate) in expected.items():
            with self.subTest(layer=layer):
                profile=resolve_depth_output_profile(ROOT,layer)
                self.assertEqual(Path(profile['path']).name,filename)
                self.assertEqual(profile['rate_hz'],rate)

    def test_api_and_asic_serials_are_loaded_as_distinct_rig_fields(self):
        identity=read_device_identity(ROOT)
        raw=json.loads((ROOT/'config/hardware/rig.json').read_text())['identity']
        self.assertEqual(identity,{'api_serial':raw['api_serial'],
                                  'asic_usb_serial':raw['asic_usb_serial']})
        self.assertNotEqual(identity['api_serial'],identity['asic_usb_serial'])
        enumeration=('Device info:\n'
                      '    Name                          :     Intel RealSense D435I\n'
                      '    Serial Number                 :     '+identity['api_serial']+'\n'
                      '    Asic Serial Number            :     '+identity['asic_usb_serial']+'\n'
                      '    Physical Port                 :     2-1.4-4\n')
        self.assertEqual(match_observed_device_identity(identity,enumeration),{
            'api_serial':identity['api_serial'],
            'asic_usb_serial':identity['asic_usb_serial'],
            'physical_port':'2-1.4-4'})
        split_records=('Device info:\n Serial Number: '+identity['api_serial']+'\n'
                       'Device info:\n Asic Serial Number: '+identity['asic_usb_serial']+'\n')
        with self.assertRaisesRegex(ValueError,'exactly one device record'):
            match_observed_device_identity(identity,split_records)
        duplicated=enumeration.replace('Device info:',
            'Device info:\n Serial Number: '+identity['api_serial'],1)
        with self.assertRaisesRegex(ValueError,'exactly one device record'):
            match_observed_device_identity(identity,duplicated)
        multiple=enumeration+'\n'+enumeration
        with self.assertRaisesRegex(ValueError,'exactly one device record'):
            match_observed_device_identity(identity,multiple)
        result=subprocess.run([
            sys.executable,str(ROOT/'tools/hardware_profile.py'),
            '--match-device-identity','--api-serial',identity['api_serial'],
            '--asic-usb-serial',identity['asic_usb_serial']],
            input=enumeration,text=True,capture_output=True,check=True)
        self.assertEqual(result.stdout.splitlines(),[
            identity['api_serial'],identity['asic_usb_serial'],'2-1.4-4'])

    def test_invalid_rate_or_missing_device_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cfg=root/'config/hardware';cfg.mkdir(parents=True)
            (cfg/'sensor_runtime.json').write_text('{"depth_output_rate_hz": -1}')
            with self.assertRaisesRegex(ValueError,'depth_output_rate_hz'):
                resolve_depth_output_profile(root,'sensors')
            (cfg/'rig.json').write_text('{"identity":{"api_serial":"12"}}')
            with self.assertRaisesRegex(ValueError,'API and ASIC'):
                read_device_identity(root)

    def test_install_manifest_detects_source_and_binary_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); install=root/'install'; source=root/'src/own/uav_sensor_interface'
            source.mkdir(parents=True); (source/'depth.cpp').write_text('source-v1')
            binary=install/'uav_sensor_interface/lib/uav_sensor_interface/d435i_depth_to_meters_cpp'
            binary.parent.mkdir(parents=True); binary.write_bytes(b'binary-v1')
            manifest=build_manifest.expected(root,install)
            (install/'.hardware-build.json').write_text(json.dumps(manifest))
            self.assertEqual(build_manifest.expected(root,install),manifest)
            (source/'depth.cpp').write_text('source-v2')
            self.assertNotEqual(build_manifest.expected(root,install),manifest)
            (source/'depth.cpp').write_text('source-v1')
            binary.write_bytes(b'binary-v2')
            self.assertNotEqual(build_manifest.expected(root,install),manifest)

    def test_install_manifest_covers_launch_and_config_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);install=root/'install'
            source=root/'src/own/uav_sensor_interface'
            for relative,content in (('launch/d435i.launch.py','launch-v1'),
                                     ('config/d435i_camera.yaml','config-v1'),
                                     ('package.xml','package-v1')):
                path=source/relative;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(content)
                target=install/'share/uav_sensor_interface'/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(content)
            binary=install/'uav_sensor_interface/lib/uav_sensor_interface/d435i_depth_to_meters_cpp'
            binary.parent.mkdir(parents=True);binary.write_bytes(b'binary')
            manifest=build_manifest.expected(root,install)
            for relative in ('share/uav_sensor_interface/launch/d435i.launch.py',
                             'share/uav_sensor_interface/config/d435i_camera.yaml'):
                self.assertIn(relative,manifest['installed_artifacts'])
            (install/'share/uav_sensor_interface/config/d435i_camera.yaml').write_text('stale')
            with self.assertRaisesRegex(RuntimeError,'launch/config/package files differ'):
                build_manifest.expected(root,install)

    def test_session_only_skips_repeated_preflight_for_its_fixed_prefix(self):
        from hardware_profile import session_preflighted
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); state_dir=root/'.runtime';state_dir.mkdir()
            install=root/'install';install.mkdir()
            config=root/'config/hardware';config.mkdir(parents=True)
            rig={'identity':{'api_serial':'12','asic_usb_serial':'34'}}
            (config/'rig.json').write_text(json.dumps(rig))
            identity={'api_serial':'12','asic_usb_serial':'34'}
            state={'operation':'session','session_id':'abc','phase':'starting',
                   'install_base':str(install),'device_identity':identity,
                   'config_sha256':hardware_config_hashes(root)}
            (state_dir/'hardware-session.json').write_text(json.dumps(state))
            self.assertTrue(session_preflighted(root,'abc',install))
            self.assertFalse(session_preflighted(root,'other',install))
            self.assertFalse(session_preflighted(root,'abc',root/'other'))
            rig['identity']['api_serial']='99'
            (config/'rig.json').write_text(json.dumps(rig))
            self.assertFalse(session_preflighted(root,'abc',install))


if __name__=='__main__': unittest.main()
