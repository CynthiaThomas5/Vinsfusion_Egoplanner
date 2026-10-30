"""Launcher routing/state tests with fake Docker; real SITL is verified separately."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FAKE = r'''
import json, os, pathlib, sys
root = pathlib.Path(os.environ['LAUNCHER_TEST_ROOT'])
state = json.loads((root / 'state.json').read_text())
tool, *args = sys.argv[1:]
if tool == 'docker':
    if args[0] == 'info':
        sys.exit(state.get('docker_error', 0))
    if args[0] == 'ps':
        print(state.get('active', ''))
    if args[0] == 'inspect':
        if '.Config.Env' in ' '.join(args):
            print(json.dumps(['PROJECT_GUI=1'] if state.get('gui', True) else []))
        else:
            print('true' if state.get('running', True) else 'false')
elif tool == 'project':
    calls = json.loads((root / 'calls.json').read_text())
    calls.append(args)
    (root / 'calls.json').write_text(json.dumps(calls))
    action, run = args[:2]
    if action == 'stop':
        state['active'] = ''
    if action == 'sim':
        if state.get('start_error'):
            sys.exit(state['start_error'])
        state['active'] = 'd435i-' + run
        path = root / 'artifacts/runs' / run
        path.mkdir(parents=True)
        (path / 'stack-started').touch()
    (root / 'state.json').write_text(json.dumps(state))
    if action == 'mission':
        sys.exit(state.get('mission_exit', 0))
elif tool == 'ps':
    print('/usr/lib/xorg/Xorg :11 -auth ' + state['authority'])
elif tool == 'xdpyinfo':
    sys.exit(0 if os.environ.get('DISPLAY') == ':11' and
             os.environ.get('XAUTHORITY') == state['authority'] else 1)
'''


class StartLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='d435i launcher ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.auth_tmp = tempfile.TemporaryDirectory(prefix='d435i-auth-')
        self.addCleanup(self.auth_tmp.cleanup)
        authority = str(Path(self.auth_tmp.name) / 'Xauthority')
        shutil.copyfile(ROOT / 'start.sh', self.root / 'start.sh')
        (self.root / 'bin').mkdir()
        (self.root / 'tools').mkdir()
        (self.root / 'config/components/simulation').mkdir(parents=True)
        shutil.copyfile(ROOT / 'config/components/simulation/scenes.json',
                        self.root / 'config/components/simulation/scenes.json')
        shutil.copyfile(ROOT / 'tools/scene_config.py', self.root / 'tools/scene_config.py')
        Path(authority).touch()
        (self.root / 'fake.py').write_text(FAKE)
        for tool in ['docker', 'ps', 'xdpyinfo', 'project']:
            target = self.root / ('tools/project.sh' if tool == 'project' else 'bin/' + tool)
            target.write_text('#!/usr/bin/env bash\nexec python3 "$LAUNCHER_TEST_ROOT/fake.py" '
                              + tool + ' "$@"\n')
            target.chmod(0o755)
        (self.root / 'calls.json').write_text('[]')
        self.env = {**os.environ, 'LAUNCHER_TEST_ROOT': str(self.root),
                    'PATH': str(self.root / 'bin') + os.pathsep + os.environ['PATH'],
                    'DISPLAY': ':11', 'XAUTHORITY': authority}
        self.state = {'active': 'd435i-old', 'authority': authority}

    def run_launcher(self, *args):
        (self.root / 'state.json').write_text(json.dumps(self.state))
        return subprocess.run(['bash', str(self.root / 'start.sh'), *args],
                              env=self.env, capture_output=True, text=True, timeout=10)

    def calls(self):
        return json.loads((self.root / 'calls.json').read_text())

    def old_run(self):
        path = self.root / 'artifacts/runs/old'
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_default_reuses_gui_without_flight(self):
        self.assertEqual(self.run_launcher().returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_ssh_start_detects_desktop_and_generates_new_id(self):
        self.state['active'] = ''
        self.env.pop('DISPLAY')
        self.env.pop('XAUTHORITY')
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], 'sim')
        self.assertTrue(calls[0][1].startswith('gui-'))
        self.assertEqual(calls[0][2], '--gui')
        self.assertIn('桌面 :11', result.stdout)

    def test_fly_delegates_and_preserves_mission_failure(self):
        self.state['mission_exit'] = 23
        self.assertEqual(self.run_launcher('fly').returncode, 23)
        self.assertEqual(self.calls(), [['mission', 'old']])

    def test_completed_flight_starts_fresh_epoch_before_next_mission(self):
        path = self.old_run()
        (path / 'flight-probe-ready').touch()
        (path / 'flight.json').write_text(json.dumps({'result': 'PASS', 'landed_and_disarmed': True}))
        (path / 'qualification.json').write_text('{"passed": true}')
        result = self.run_launcher('fly')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertEqual([c[0] for c in calls], ['stop', 'sim', 'mission'])
        self.assertNotEqual(calls[1][1], 'old')
        self.assertEqual(calls[1][1], calls[2][1])

    def test_active_or_unconfirmed_flight_cannot_be_stopped_or_restarted(self):
        path = self.old_run()
        (path / 'flight-probe-ready').touch()
        for action in ['stop', 'fly']:
            self.assertNotEqual(self.run_launcher(action).returncode, 0)
        (path / 'flight.json').write_text('{"result": "FAIL", "landed_and_disarmed": false}')
        self.assertNotEqual(self.run_launcher('stop').returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_stop_waits_for_postprocessing_then_delegates(self):
        path = self.old_run()
        (path / 'preflight.json').write_text('{}')
        (path / 'flight.json').write_text('{"result": "PASS", "landed_and_disarmed": true}')
        self.assertNotEqual(self.run_launcher('stop').returncode, 0)
        (path / 'qualification.json').write_text('{"passed": true}')
        self.assertEqual(self.run_launcher('stop').returncode, 0)
        self.assertEqual(self.calls(), [['stop', 'old']])

    def test_no_flight_on_startup_failure(self):
        self.state.update(active='', start_error=17)
        self.assertEqual(self.run_launcher('fly').returncode, 17)
        self.assertEqual([c[0] for c in self.calls()], ['sim'])

    def test_rejects_headless_and_multiple_active_sessions(self):
        self.state['gui'] = False
        self.assertNotEqual(self.run_launcher().returncode, 0)
        self.state['active'] = 'd435i-a\nd435i-b'
        self.assertNotEqual(self.run_launcher('fly').returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_explicit_scene_switch_restarts_unarmed_gui(self):
        result = self.run_launcher('start', 'floorplan2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([c[0] for c in self.calls()], ['stop', 'sim'])

    def test_scene_switch_refuses_unconfirmed_flight(self):
        (self.old_run()/'flight-probe-ready').touch()
        self.assertNotEqual(self.run_launcher('start', 'floorplan2').returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_repeat_fly_without_scene_preserves_active_scene(self):
        path = self.old_run()
        (path/'world.json').write_text('{"scene":"floorplan2"}')
        result = self.run_launcher('fly')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [['mission', 'old']])

    def test_unknown_scene_does_not_stop_existing_gui(self):
        self.assertNotEqual(self.run_launcher('start', 'unknown').returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_status_works_while_another_launcher_holds_lock(self):
        (self.root / '.runtime').mkdir()
        with (self.root / '.runtime/start.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.run_launcher('status').returncode, 0)
            self.assertEqual(self.run_launcher('fly').returncode, 9)
        self.assertEqual(self.calls(), [])


if __name__ == '__main__':
    unittest.main()
