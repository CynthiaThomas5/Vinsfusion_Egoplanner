#!/usr/bin/env python3
"""Host command boundaries, without Docker or vehicle access."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import io
import sys
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


class GroundstationTests(unittest.TestCase):
    def test_qgc_only_forwards_rx_to_localhost(self):
        sys.path.insert(0,str(ROOT/'tools/diagnostics'))
        import qgc_readonly as relay
        from relay_hw08_serial import HEADER
        child = MagicMock()
        child.stdout = io.BytesIO(HEADER.pack(2,1,2,0)+HEADER.pack(1,3,4,3)+b'abc')
        child.wait.return_value = 0
        process = MagicMock(); process.__enter__.return_value = child
        udp = MagicMock()
        sock = MagicMock(); sock.__enter__.return_value = udp
        with patch.object(relay.subprocess,'Popen',return_value=process), \
             patch.object(relay.socket,'socket',return_value=sock), \
             patch.object(sys,'argv',['qgc_readonly','--host','fixture','--root','/fixture']):
            relay.main()
        udp.sendto.assert_called_once_with(b'abc',('127.0.0.1',14550))
        self.assertEqual([call[0] for call in udp.method_calls],['sendto'])

    def test_no_implicit_vehicle_action_and_no_control_start(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            record = path / 'calls'
            for command in ('ssh', 'docker'):
                stub = path / command
                stub.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\n')
                stub.chmod(0o755)
            env = dict(os.environ, PATH=str(path)+':'+os.environ['PATH'],
                       CALLS=str(record), XDG_STATE_HOME=str(path/'state'))
            def run(*args):
                return subprocess.run(['bash',str(ROOT/'tools/groundstation.sh'),*args],
                                      env=env,capture_output=True,text=True)
            self.assertEqual(run().returncode,0)
            self.assertFalse(record.exists())
            for layer in ('control', 'ev', 'full-load', 'plan;echo bad'):
                self.assertNotEqual(run('nano-start',layer).returncode,0)
            self.assertFalse(record.exists())
            self.assertEqual(run('nano-start','plan').returncode,0)
            self.assertIn("hardware.sh start 'plan'",record.read_text())
            record.unlink()
            self.assertEqual(run('nano-ros','topic','echo','/example;literal').returncode,0)
            self.assertIn('/example\\;literal',record.read_text())

    def test_experiment_stop_refuses_control_layer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            record = path / 'calls'
            ssh = path / 'ssh'
            ssh.write_text('#!/bin/sh\nprintf "ssh %s\\n" "$*" >> "$CALLS"\nprintf \'{"layer":"control"}\\n\'\n')
            ssh.chmod(0o755)
            docker = path / 'docker'
            docker.write_text('#!/bin/sh\nprintf "docker %s\\n" "$*" >> "$CALLS"\nexit 1\n')
            docker.chmod(0o755)
            env = dict(os.environ, PATH=str(path)+':'+os.environ['PATH'],
                       CALLS=str(record), XDG_STATE_HOME=str(path/'state'))
            result = subprocess.run(['bash',str(ROOT/'tools/groundstation.sh'),
                                     'experiment-stop'],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('layer control',result.stderr)
            calls=record.read_text()
            self.assertIn('hardware.sh status',calls)
            self.assertNotIn('hardware.sh stop',calls)
            self.assertNotIn('docker',calls)

    def test_experiment_stop_saves_viewer_log_before_removing_container(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); root=base/'project'; (root/'tools').mkdir(parents=True)
            (root/'config/groundstation').mkdir(parents=True)
            shutil.copy2(ROOT/'tools/groundstation.sh',root/'tools/groundstation.sh')
            shutil.copy2(ROOT/'config/groundstation/debian.env',root/'config/groundstation/debian.env')
            fakebin=base/'fakebin'; fakebin.mkdir()
            calls=base/'calls'
            ssh=fakebin/'ssh'
            ssh.write_text('#!/bin/sh\nprintf \'{"layer":"perception","run_id":"test-run"}\\n\'\n')
            ssh.chmod(0o755)
            docker=fakebin/'docker'
            docker.write_text('''#!/bin/sh
printf "%s\\n" "$*" >> "$CALLS"
case "$1" in
  inspect|stop|rm) exit 0 ;;
  logs) echo 'viewer retained log'; exit 0 ;;
  *) exit 1 ;;
esac
''')
            docker.chmod(0o755)
            env=dict(os.environ,PATH=str(fakebin)+':'+os.environ['PATH'],CALLS=str(calls),XDG_STATE_HOME=str(base/'state'))
            result=subprocess.run(['bash',str(root/'tools/groundstation.sh'),'experiment-stop'],
                                  env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            log=root/'artifacts/runs/test-run/groundstation/viewer-console.log'
            self.assertEqual(log.read_text(),'viewer retained log\n')
            commands=calls.read_text().splitlines()
            self.assertLess(commands.index('logs d435i-gs-view'),commands.index('rm d435i-gs-view'))

    def test_desktop_launcher_keeps_rollbackable_project_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); releases=base/'releases/current'; project=releases/'project'
            (project/'tools').mkdir(parents=True)
            shutil.copy2(ROOT/'tools/install_groundstation_desktop.py',
                         project/'tools/install_groundstation_desktop.py')
            alias=base/'project'; alias.symlink_to(project, target_is_directory=True)
            bindir=base/'.local/bin'
            (bindir.parent/'share/applications').mkdir(parents=True)
            fakebin=base/'fakebin'; fakebin.mkdir()
            xdg=fakebin/'xdg-user-dir'; xdg.write_text('#!/bin/sh\nprintf "%s/Desktop\\n" "$HOME"\n'); xdg.chmod(0o755)
            gio=fakebin/'gio'; gio.write_text('#!/bin/sh\nexit 0\n'); gio.chmod(0o755)
            env=dict(os.environ, HOME=str(base), PATH=str(fakebin)+':'+os.environ['PATH'])
            result=subprocess.run(['python3',str(alias/'tools/install_groundstation_desktop.py')],
                                  env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            content=(bindir/'uav-groundstation').read_text()
            self.assertIn(str(alias/'tools/groundstation.sh'),content)
            self.assertNotIn(str(project/'tools/groundstation.sh'),content)


if __name__ == '__main__':
    unittest.main()
