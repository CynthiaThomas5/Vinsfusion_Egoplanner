#!/usr/bin/env python3
"""Owned-process identity and ground/flight stop boundary checks."""
import importlib.util
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import threading
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('hardware_session',Path(__file__).with_name('hardware-session.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def add_realsense_fixture(root):
    patch=root/'dependencies/patches/realsense/clock.patch'
    patch.parent.mkdir(parents=True,exist_ok=True)
    patch.write_text('fixture-patch')
    deployment={
        'ros_overlay':'/fixture/overlay/local_setup.bash',
        'wrapper_source_dir':'/fixture/wrapper/src',
        'wrapper_install_prefix':'/fixture/wrapper/install/package',
        'wrapper_version':'3.2.3','wrapper_source_commit':'a'*40,
        'wrapper_library_sha256':'b'*64,'sdk_source_dir':'/fixture/sdk/src',
        'hid_sensitivity_patch':'/fixture/sdk.patch',
        'hid_sensitivity_patch_sha256':'c'*64}
    profile={'schema':1,'version':'2.58.1','library_dir':'sdk/lib',
             'library_sha256':'d'*64,'base_commit':'e'*40,
             'clock_patch':'dependencies/patches/realsense/clock.patch',
             'clock_patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),
             'deployment':deployment}
    (root/'config/hardware/realsense_sdk.json').write_text(json.dumps(profile))


def add_hardware_config(root):
    config=root/'config/hardware';config.mkdir(parents=True,exist_ok=True)
    (config/'mapping.json').write_text('{"depth_output_rate_hz":5.0}')
    (config/'sensor_runtime.json').write_text('{"depth_output_rate_hz":3.0}')
    (config/'planner.json').write_text('{"depth_output_rate_hz":3.0}')
    (config/'rig.json').write_text(
        '{"identity":{"api_serial":"123","asic_usb_serial":"456"}}')
    add_realsense_fixture(root)


class SessionTests(TestCase):
    def test_invalid_start_options_are_rejected_before_preflight_or_state(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); state_path=root/'.runtime/state.json'
            for argv in (['hardware-session.py','start','map','--measure-seconds','nan'],
                         ['hardware-session.py','start','sensors','--visuals']):
                with patch.object(m,'ROOT',root),patch.object(m,'STATE',state_path), \
                        patch.object(m.os,'uname',return_value=SimpleNamespace(machine='aarch64')), \
                        patch.object(m,'run') as run,patch('sys.argv',argv):
                    with self.assertRaises(ValueError): m.main()
                    run.assert_not_called()
                    self.assertFalse(state_path.exists())
                    self.assertFalse((root/'artifacts/runs').exists())

    def test_failed_install_preflight_creates_no_run_or_session(self):
        import subprocess
        with TemporaryDirectory() as tmp:
            root=Path(tmp); state_path=root/'.runtime/state.json'
            config=root/'config/hardware';config.mkdir(parents=True)
            (config/'mapping.json').write_text('{"depth_output_rate_hz":5.0}')
            (config/'rig.json').write_text(
                '{"identity":{"api_serial":"123","asic_usb_serial":"456"}}')
            add_realsense_fixture(root)
            with patch.object(m,'ROOT',root),patch.object(m,'STATE',state_path), \
                    patch.object(m.os,'uname',return_value=SimpleNamespace(machine='aarch64')), \
                    patch.object(m,'run',side_effect=subprocess.CalledProcessError(1,['check'])), \
                    patch('sys.argv',['hardware-session.py','start','map','--run-id','preflight-fail']):
                with self.assertRaises(subprocess.CalledProcessError): m.main()
            self.assertFalse(state_path.exists())
            self.assertFalse((root/'artifacts/runs/preflight-fail').exists())

    def test_start_failure_after_reservation_cleans_owned_state(self):
        import subprocess
        with TemporaryDirectory() as tmp:
            root=Path(tmp); state_path=root/'.runtime/hardware-session.json'
            config=root/'config/hardware';config.mkdir(parents=True)
            (config/'sensor_runtime.json').write_text('{"depth_output_rate_hz":3.0}')
            (config/'rig.json').write_text(
                '{"identity":{"api_serial":"123","asic_usb_serial":"456"}}')
            add_realsense_fixture(root)
            failure=subprocess.CalledProcessError(1,['sensor-start'])
            with patch.object(m,'ROOT',root),patch.object(m,'STATE',state_path), \
                    patch.object(m.os,'uname',return_value=SimpleNamespace(machine='aarch64')), \
                    patch.object(m,'run',side_effect=[None,failure]), \
                    patch('sys.argv',['hardware-session.py','start','perception','--run-id','startup-fail']):
                with self.assertRaises(subprocess.CalledProcessError): m.main()
            self.assertFalse(state_path.exists())
            self.assertTrue((root/'artifacts/runs/startup-fail/session-exit.json').exists())

    def test_failures_after_start_reservation_use_one_cleanup_path(self):
        import subprocess
        for failure_stage in ('sysctl','config','map','plan','localization'):
            with self.subTest(stage=failure_stage),TemporaryDirectory() as tmp:
                root=Path(tmp);add_hardware_config(root)
                runtime=root/'.runtime';runtime.mkdir(exist_ok=True)
                state_path=runtime/'hardware-session.json'
                layer='plan' if failure_stage=='plan' else ('map' if failure_stage=='map' else 'perception')
                run_id='fail-'+failure_stage
                calls=[]
                failure=RuntimeError('injected '+failure_stage+' failure')
                def run(argv, **kwargs):
                    calls.append(argv)
                    if argv[:3]==['bash','tools/hardware.sh','sensors'] and argv[3]=='start':
                        (runtime/'hardware-sensors.state').write_text(
                            '123\n'+str(root/'artifacts/runs'/run_id)+'\n')
                        return
                    if argv[:2]==['bash','tools/hardware-localization.sh'] and argv[2]=='start':
                        (runtime/'hw04-localization.state').write_text(
                            '1\n2\n3\nepoch\nsession\n'+str(root/'artifacts/runs'/run_id)+'\n')
                        if failure_stage=='localization': raise failure
                        return
                    if argv[:2]==['bash','tools/hardware-localization.sh'] and argv[2]=='stop':
                        (runtime/'hw04-localization.state').unlink(missing_ok=True)
                        return
                    if argv[:3]==['bash','tools/hardware.sh','sensors'] and argv[3]=='stop':
                        (runtime/'hardware-sensors.state').unlink(missing_ok=True)
                        return
                    if argv and argv[0]=='sudo':
                        if failure_stage=='sysctl' and argv[-1].endswith('=8388608'):
                            raise failure
                        return
                    if len(argv)>1 and argv[:2]==['python3','tools/generate_vins_config.py']:
                        if failure_stage=='config': raise failure
                        session=Path(argv[argv.index('--output')+1])
                        session.mkdir(parents=True,exist_ok=True)
                        (session/'session.json').write_text(json.dumps({'epoch':'a'*32}))
                        return
                def spawn(state,name,argv,env):
                    state['processes'].append({'name':name,'pid':99999999,
                        'start_ticks':None,'log':str(Path(state['run_dir'])/(name+'.log'))})
                    m.save(state)
                    if failure_stage==name: raise failure
                real_read_text=Path.read_text
                def read_text(path,*args,**kwargs):
                    if str(path)=='/proc/sys/net/core/rmem_max': return '212992'
                    return real_read_text(path,*args,**kwargs)
                with patch.object(m,'ROOT',root),patch.object(m,'STATE',state_path), \
                        patch.object(m.os,'uname',return_value=SimpleNamespace(machine='aarch64')), \
                        patch.object(m,'run',side_effect=run),patch.object(m,'spawn',side_effect=spawn), \
                        patch.object(Path,'read_text',read_text), \
                        patch('sys.argv',['hardware-session.py','start',layer,'--run-id',run_id]), \
                        contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises((RuntimeError,subprocess.CalledProcessError)):
                        m.main()
                self.assertFalse(state_path.exists())
                self.assertTrue((root/'artifacts/runs'/run_id/'session-exit.json').exists())
                self.assertFalse((runtime/'hardware-sensors.state').exists())
                self.assertFalse((runtime/'hw04-localization.state').exists())
                self.assertIn(['sudo','-n','sysctl','-w','net.core.rmem_max=212992'],calls)

    def test_ev_startup_cleanup_allowed_only_before_bridge_attempt(self):
        with TemporaryDirectory() as tmp,patch.object(m,'ROOT',Path(tmp)), \
                patch.object(m,'STATE',Path(tmp)/'.runtime/state.json'),patch.object(m,'run'):
            state={'layer':'ev','run_id':'ev','session_id':'ev','run_dir':tmp,'processes':[],
                   'bridge_start_attempted':False}
            m.STATE.parent.mkdir(exist_ok=True)
            m.STATE.write_text(json.dumps(state))
            m.stop(state,startup_failure=True)
            self.assertFalse(m.STATE.exists())
            state['bridge_start_attempted']=True
            m.STATE.write_text(json.dumps(state))
            with self.assertRaisesRegex(RuntimeError,'confirmation'):
                m.stop(state,startup_failure=True)

    def test_only_one_concurrent_reservation_wins(self):
        with TemporaryDirectory() as tmp,patch.object(m,'STATE',Path(tmp)/'state.json'):
            barrier=threading.Barrier(2); results=[]
            def contender(label):
                state={'session_id':label,'run_id':label}
                barrier.wait()
                try: m.reserve(state); results.append(('ok',label))
                except FileExistsError: results.append(('busy',label))
            threads=[threading.Thread(target=contender,args=(label,)) for label in ('one','two')]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            self.assertEqual(sorted(result[0] for result in results),['busy','ok'])
            winner=json.loads(m.STATE.read_text())['session_id']
            m.remove_reservation({'session_id':'loser','run_id':'loser'})
            self.assertTrue(m.STATE.exists())
            m.remove_reservation({'session_id':winner,'run_id':winner})
            self.assertFalse(m.STATE.exists())

    def test_build_reservation_uses_the_session_gate_until_release(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);state_path=root/'.runtime/hardware-session.json'
            with patch.object(m,'ROOT',root),patch.object(m,'STATE',state_path), \
                    patch('sys.argv',['hardware-session.py','reserve-build',
                                      '--build-id','build-fixture',
                                      '--owner-pid',str(os.getpid())]), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                m.main()
            state=json.loads(state_path.read_text())
            self.assertEqual(state['operation'],'build')
            self.assertEqual(state['phase'],'building')
            with patch.object(m,'ROOT',root),patch.object(m,'STATE',state_path), \
                    patch.object(m.os,'uname',return_value=SimpleNamespace(machine='aarch64')), \
                    patch.object(m,'run') as run, \
                    patch('sys.argv',['hardware-session.py','start','map','--run-id','blocked']):
                with self.assertRaisesRegex(RuntimeError,'Session exists'):
                    m.main()
                run.assert_not_called()
                with self.assertRaisesRegex(RuntimeError,'still active'):
                    m.stop(state)
            with patch.object(m,'STATE',state_path):
                m.release_build(state['session_id'])
            self.assertFalse(state_path.exists())

    def test_map_prewarms_without_navigation_or_bridge(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.runtime').mkdir();(root/'config/hardware').mkdir(parents=True)
            (root/'config/hardware/mapping.json').write_text('{"depth_output_rate_hz":5.0}')
            (root/'config/hardware/sensor_runtime.json').write_text('{"depth_output_rate_hz":3.0}')
            (root/'config/hardware/planner.json').write_text('{"depth_output_rate_hz":3.0}')
            (root/'config/hardware/rig.json').write_text(
                '{"identity":{"api_serial":"123","asic_usb_serial":"456"}}')
            add_realsense_fixture(root)
            events=[];spawned=[];run_calls=[]
            def run(argv, **kwargs):
                events.append(argv);run_calls.append((argv,kwargs))
                if 'tools/generate_vins_config.py' in argv:
                    session=Path(argv[argv.index('--output')+1]);session.mkdir(parents=True)
                    (session/'session.json').write_text(json.dumps({'epoch':'a'*32}))
            def spawn(state,name,argv,env):
                events.append(['spawn',name]);spawned.append((name,argv))
            with patch.object(m,'ROOT',root),patch.object(m,'STATE',root/'.runtime/state.json'), \
                    patch.object(m.os,'uname',return_value=SimpleNamespace(machine='aarch64')), \
                    patch.object(m,'run',side_effect=run),patch.object(m,'spawn',side_effect=spawn), \
                    patch('sys.argv',['hardware-session.py','start','map','--run-id','test-map']), \
                    contextlib.redirect_stdout(io.StringIO()):
                m.main()
            self.assertEqual(len(spawned),1)
            self.assertEqual(spawned[0][0],'map')
            self.assertIn('hardware_mapping.launch.py',spawned[0][1])
            self.assertNotIn('hardware_plan.launch.py',spawned[0][1])
            sensor_env=next(kwargs['env'] for argv,kwargs in run_calls
                            if argv[:3]==['bash','tools/hardware.sh','sensors'])
            self.assertEqual(sensor_env['HW_DEPTH_OUTPUT_HZ'],'5.0')
            localization=next(i for i,v in enumerate(events) if 'tools/hardware-localization.sh' in v)
            self.assertLess(events.index(['spawn','map']),localization)
            saved=json.loads((root/'.runtime/state.json').read_text())
            self.assertEqual(saved['layer'],'map')
            self.assertEqual(saved['depth_profile'],'config/hardware/mapping.json')
            self.assertEqual(saved['depth_output_rate_hz'],5.0)
            self.assertEqual(saved['depth_profile_sha256'],hashlib.sha256(
                (root/'config/hardware/mapping.json').read_bytes()).hexdigest())
            self.assertEqual(saved['rig_sha256'],saved['config_sha256']['config/hardware/rig.json'])

    def test_missing_identity_never_counts_as_alive(self):
        with patch.object(m,'identity',return_value=None):
            self.assertFalse(m.alive({'pid':987654,'start_ticks':None}))

    def test_reused_pid_is_not_signalled(self):
        item={'pid':123,'start_ticks':'before','name':'plan'}
        with TemporaryDirectory() as tmp, patch.object(m,'identity',return_value='after'), patch.object(m.os,'killpg',side_effect=ProcessLookupError) as kill:
            root=Path(tmp);(root/'.runtime').mkdir();state_path=root/'.runtime/state.json';state_path.write_text('{}')
            with patch.object(m,'ROOT',root),patch.object(m,'STATE',state_path):
                m.stop({'layer':'plan','processes':[item],'run_dir':tmp})
            kill.assert_not_called()

    def test_control_unknown_state_preserves_monitoring(self):
        for layer in ('ev','control'):
            with patch.object(m.os,'killpg') as kill:
                with self.assertRaisesRegex(RuntimeError,'confirmation'):
                    m.stop({'layer':layer,'processes':[]})
                kill.assert_not_called()

    def test_ground_cleanup_restores_only_recorded_buffer(self):
        with TemporaryDirectory() as tmp,patch.object(m,'run') as run:
            root=Path(tmp);(root/'.runtime').mkdir();state_path=root/'.runtime/state.json';state_path.write_text('{}')
            (root/'.runtime/hw04-localization.state').write_text('1\n2\n3\nepoch\nsession\n'+tmp+'\n')
            (root/'.runtime/hardware-sensors.state').write_text('1\n'+tmp+'\n')
            state={'layer':'full-load','processes':[],'run_dir':tmp,'rmem_original':212992}
            with patch.object(m,'ROOT',root),patch.object(m,'STATE',state_path):
                m.stop(state)
            self.assertEqual([call.args[0] for call in run.call_args_list],[
                ['bash','tools/hardware-localization.sh','stop'],
                ['bash','tools/hardware.sh','sensors','stop'],
                ['sudo','-n','sysctl','-w','net.core.rmem_max=212992']])
            self.assertFalse(state_path.exists());self.assertTrue((root/'session-exit.json').exists())

    def test_cleanup_refuses_to_stop_a_sidecar_from_another_run(self):
        with TemporaryDirectory() as tmp,patch.object(m,'run') as run:
            root=Path(tmp);runtime=root/'.runtime';runtime.mkdir()
            state_path=runtime/'state.json';state_path.write_text('{}')
            (runtime/'hardware-sensors.state').write_text('123\n'+str(root/'other-run')+'\n')
            state={'layer':'perception','processes':[],'run_dir':str(root/'this-run')}
            with patch.object(m,'ROOT',root),patch.object(m,'STATE',state_path):
                with self.assertRaisesRegex(RuntimeError,'not owned by this run'):
                    m.stop(state)
            run.assert_not_called()
            self.assertTrue(state_path.exists())

    def test_stop_entrypoints_do_not_require_startup_profiles_or_ros(self):
        import shutil
        import subprocess
        with TemporaryDirectory() as tmp:
            root=Path(tmp);tools=root/'tools';tools.mkdir()
            for name in ('hardware.sh','hardware-localization.sh'):
                shutil.copy2(Path(__file__).with_name(name),tools/name)
            sensor=subprocess.run(['bash',str(tools/'hardware.sh'),'sensors','stop'],
                                  text=True,capture_output=True)
            localization=subprocess.run(
                ['bash',str(tools/'hardware-localization.sh'),'stop'],
                text=True,capture_output=True)
            self.assertEqual(sensor.returncode,0,sensor.stderr)
            self.assertIn('No hardware sensor session',sensor.stdout)
            self.assertEqual(localization.returncode,0,localization.stderr)
            self.assertIn('No HW04 localization session',localization.stdout)

if __name__=='__main__':main()
