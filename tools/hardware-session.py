#!/usr/bin/env python3
"""One ground hardware session; real EV/control require qualified installed geometry."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
from hardware_profile import (read_device_identity, resolve_depth_output_profile,
                              read_realsense_deployment, selected_install_base,
                              hardware_config_hashes)

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.runtime/hardware-session.json'
LAYERS = ('sensors', 'perception', 'map', 'plan', 'ev', 'control', 'full-load')


def run(argv, **kwargs):
    return subprocess.run(argv, cwd=str(ROOT), check=True, **kwargs)


def identity(pid):
    try:
        # /proc comm can contain spaces and parentheses.
        fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except (OSError, IndexError):
        return None


def alive(item):
    return item['start_ticks'] is not None and identity(item['pid']) == item['start_ticks']


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=2)+'\n')
    tmp.replace(STATE)


def reserve(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name('.'+STATE.name+'.'+state['session_id']+'.tmp')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(json.dumps(state, indent=2)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        # Linking publishes a complete JSON reservation and fails if another
        # start already owns STATE; readers never observe a partial record.
        os.link(tmp, STATE)
    except BaseException:
        raise
    finally:
        try: tmp.unlink()
        except FileNotFoundError: pass


def remove_reservation(state):
    try:
        current = json.loads(STATE.read_text())
    except (OSError, ValueError):
        return
    if (current.get('session_id') == state.get('session_id')
            and (current.get('session_id') is not None
                 or current.get('run_id') == state.get('run_id'))):
        STATE.unlink()


def sidecar_belongs_to_run(path, state, run_dir_line):
    try:
        lines=Path(path).read_text().splitlines()
        recorded=Path(lines[run_dir_line]).resolve()
        expected=Path(state['run_dir']).resolve()
    except (OSError, IndexError, KeyError, ValueError):
        return False
    return recorded == expected


def reserve_build(build_id, owner_pid):
    if not build_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in build_id):
        raise ValueError('Invalid hardware build ID')
    owner_ticks=identity(owner_pid)
    if owner_ticks is None:
        raise RuntimeError('Hardware build owner process is unavailable')
    session_id=uuid.uuid4().hex
    stage=ROOT/'artifacts/hardware-builds'/build_id
    state={'operation':'build','layer':'build','run_id':build_id,
           'run_dir':str(stage),'session_id':session_id,'owner_pid':owner_pid,
           'owner_start_ticks':owner_ticks,'phase':'building','processes':[],
           'started_wall_s':time.time(),'bridge_start_attempted':False,
           'install_base':str(selected_install_base(ROOT))}
    reserve(state)
    return state


def release_build(session_id):
    try:
        state=json.loads(STATE.read_text())
    except (OSError,ValueError):
        raise RuntimeError('Hardware build reservation is missing')
    if state.get('operation')!='build' or state.get('session_id')!=session_id:
        raise RuntimeError('Hardware build reservation is not owned by this build')
    if identity(state.get('owner_pid',-1))!=state.get('owner_start_ticks'):
        raise RuntimeError('Hardware build owner identity changed; reservation retained')
    remove_reservation(state)


def spawn(state, name, argv, env):
    log = Path(state['run_dir']) / (name+'.log')
    with log.open('ab') as stream:
        p = subprocess.Popen(argv, cwd=str(ROOT), env=env, stdin=subprocess.DEVNULL,
                             stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    state['processes'].append({'name': name, 'pid': p.pid,
                               'start_ticks': identity(p.pid), 'log': str(log)})
    save(state)
    time.sleep(2)
    if p.poll() is not None:
        raise RuntimeError(name+' exited; inspect '+str(log))


def stop(state, startup_failure=False):
    if state.get('operation')=='build':
        if identity(state.get('owner_pid',-1))==state.get('owner_start_ticks'):
            raise RuntimeError('Hardware build is still active; reservation retained')
        remove_reservation(state)
        return
    # Only full-load/sensor/perception/map/plan sessions are physically isolated.
    # Never tear down an EV/control chain without observed landed/disarmed state.
    if state['layer'] in ('ev', 'control'):
        if not startup_failure or state.get('bridge_start_attempted'):
            raise RuntimeError('EV/control stop requires landed/disarmed confirmation; use the documented bridge landing path and inspect PX4 before stopping. Monitoring retained.')
    for item in reversed(state['processes']):
        if alive(item):
            os.killpg(item['pid'], signal.SIGINT)
            for _ in range(30):
                if not alive(item): break
                time.sleep(.1)
            if alive(item): os.killpg(item['pid'], signal.SIGTERM)
            for _ in range(30):
                if not alive(item): break
                time.sleep(.1)
            if alive(item): raise RuntimeError('Process remains; state retained: '+item['name'])
        for path in Path('/proc').glob('[0-9]*/stat'):
            try: fields = path.read_text().rsplit(')', 1)[1].split()
            except OSError: continue
            if fields[0] != 'Z' and int(fields[2]) == item['pid']:
                raise RuntimeError('Process group remains; inspect '+item['name'])
    stop_env=dict(os.environ,HW_HARDWARE_INSTALL=state.get('install_base',''),
                  HW_SESSION_ID=state.get('session_id',''))
    localization_state=ROOT/'.runtime/hw04-localization.state'
    if localization_state.exists():
        if not sidecar_belongs_to_run(localization_state,state,5):
            raise RuntimeError('Localization state is not owned by this run; refusing to stop it')
        run(['bash', 'tools/hardware-localization.sh', 'stop'],env=stop_env)
    sensor_state=ROOT/'.runtime/hardware-sensors.state'
    if sensor_state.exists():
        if not sidecar_belongs_to_run(sensor_state,state,1):
            raise RuntimeError('Sensor state is not owned by this run; refusing to stop it')
        run(['bash', 'tools/hardware.sh', 'sensors', 'stop'],env=stop_env)
    if state.get('rmem_original') is not None:
        run(['sudo', '-n', 'sysctl', '-w', 'net.core.rmem_max='+str(state['rmem_original'])])
    state['phase'] = 'stopped'
    state['stopped_wall_s'] = time.time()
    (Path(state['run_dir'])/'session-exit.json').write_text(json.dumps(state, indent=2)+'\n')
    remove_reservation(state)


def validate_start(args):
    if STATE.exists():
        raise RuntimeError('Session exists; inspect status/stop before starting')
    if args.measure_seconds is not None:
        if (args.layer != 'full-load' or not math.isfinite(args.measure_seconds)
                or args.measure_seconds <= 0):
            raise ValueError('Measurement requires full-load and a finite positive duration')
    if args.visuals and args.layer == 'sensors':
        raise ValueError('--visuals requires a VINS session; sensors layer cannot use it')
    run_id = args.run_id or time.strftime(
        'hardware-%s-%Y%m%dT%H%M%S' % args.layer, time.gmtime()) + '-%d' % os.getpid()
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in run_id):
        raise ValueError('Invalid run ID')
    if os.uname().machine != 'aarch64':
        raise RuntimeError('Start must run on Nano ARM')
    if any((ROOT/'.runtime'/p).exists() for p in ('hardware-sensors.state','hw04-localization.state')):
        raise RuntimeError('Separate sensor/localization session exists; stop its owner first')
    if args.layer in ('ev','control'):
        rig = json.loads((ROOT/'config/hardware/rig.json').read_text())['airframe_mount']
        if rig.get('status') != 'MEASURED' or not rig.get('control_usable'):
            raise RuntimeError('Real EV/control require qualified installed rig; full-load is the isolated ground path')
    resolve_depth_output_profile(ROOT, args.layer)
    read_device_identity(ROOT)
    read_realsense_deployment(ROOT)
    if (ROOT/'artifacts/runs'/run_id).exists():
        raise FileExistsError('Run directory already exists: '+run_id)
    # Validate the active Foxy installation before creating a run or reserving state.
    install_base = selected_install_base(ROOT)
    preflight_env = dict(os.environ, HW_HARDWARE_INSTALL=str(install_base))
    run(['bash','-c','source tools/hardware-env.bash || exit'],env=preflight_env)
    return run_id, install_base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('start', 'status', 'stop',
                                                'reserve-build','release-build'))
    parser.add_argument('layer', nargs='?', choices=LAYERS, default='perception')
    parser.add_argument('--run-id')
    parser.add_argument('--build-id')
    parser.add_argument('--session-id')
    parser.add_argument('--owner-pid',type=int)
    parser.add_argument('--measure-seconds', type=float)
    parser.add_argument('--visuals', action='store_true', help='Wait for the PC-owned visualization relay before VINS starts')
    args = parser.parse_args()
    if args.operation=='reserve-build':
        if args.build_id is None or args.owner_pid is None:
            raise SystemExit('reserve-build requires --build-id and --owner-pid')
        print(reserve_build(args.build_id,args.owner_pid)['session_id'])
        return
    if args.operation=='release-build':
        if args.session_id is None:
            raise SystemExit('release-build requires --session-id')
        release_build(args.session_id)
        return
    if args.operation == 'status':
        if not STATE.exists():
            print('No unified hardware session.'); return
        state = json.loads(STATE.read_text())
        for item in state['processes']: item['alive'] = alive(item)
        for label, filename, indices in [('sensors','hardware-sensors.state',[0]),
                ('localization','hw04-localization.state',[1,2])]:
            path = ROOT/'.runtime'/filename
            lines = path.read_text().splitlines() if path.exists() else []
            state[label] = [{'pid':int(lines[i]), 'alive': identity(int(lines[i])) is not None}
                            for i in indices if i < len(lines)]
        print(json.dumps(state, indent=2)); return
    if args.operation == 'stop':
        if STATE.exists(): stop(json.loads(STATE.read_text()))
        else: print('No unified hardware session.')
        return
    run_id, install_base = validate_start(args)
    out = ROOT/'artifacts/runs'/run_id
    depth_profile = resolve_depth_output_profile(ROOT, args.layer)
    device_identity = read_device_identity(ROOT)
    realsense = read_realsense_deployment(ROOT)
    config_sha256=hardware_config_hashes(ROOT)
    depth_profile_sha256=hashlib.sha256(
        (ROOT/depth_profile['path']).read_bytes()).hexdigest()
    rig_sha256=config_sha256['config/hardware/rig.json']
    state = {'operation':'session','layer':args.layer, 'run_id':run_id, 'run_dir':str(out),
             'session_id':uuid.uuid4().hex, 'owner_pid':os.getpid(),
             'phase':'starting', 'epoch':None, 'processes':[],
             'started_wall_s':time.time(), 'bridge_start_attempted':False,
             'install_base':str(install_base),
             'depth_output_rate_hz':depth_profile['rate_hz'],
             'depth_profile':depth_profile['path'],
             'depth_profile_sha256':depth_profile_sha256,
             'rig_sha256':rig_sha256,
             'config_sha256':config_sha256,
             'device_identity':device_identity,
             'px4_outputs':'disabled' if args.layer=='full-load' else 'not_started'}
    try:
        reserve(state)
    except FileExistsError as exc:
        raise RuntimeError('Session exists; inspect status/stop before starting') from exc
    try:
        out.mkdir(parents=True, exist_ok=False)
    except BaseException:
        remove_reservation(state)
        raise
    env = dict(os.environ, HW02_RUN_ID=run_id, HW02_ENABLE_COLOR='false',
               HW_DEPTH_OUTPUT_HZ=str(depth_profile['rate_hz']),
               HW_D435I_API_SERIAL=device_identity['api_serial'],
               HW_HARDWARE_INSTALL=str(install_base),HW_SESSION_ID=state['session_id'],
               HW_REALSENSE_OVERLAY=realsense['overlay'],
               HW_REALSENSE_SDK_LIB=realsense['sdk_lib'],
               HW_REALSENSE_SOURCE_DIR=realsense['wrapper_source_dir'],
               HW_REALSENSE_WRAPPER_PREFIX=realsense['wrapper_prefix'],
               HW_REALSENSE_SDK_SOURCE_DIR=realsense['sdk_source_dir'],
               HW_REALSENSE_SDK_PATCH=realsense['sdk_patch'])
    try:
        run(['bash','tools/hardware.sh','sensors','start'], env=env)
        if args.layer == 'sensors':
            state['phase']='running'; save(state)
            print(json.dumps(state,indent=2)); return
        old = int(Path('/proc/sys/net/core/rmem_max').read_text())
        state['rmem_original'] = old; save(state)
        if old < 8388608: run(['sudo','-n','sysctl','-w','net.core.rmem_max=8388608'])
        with (out/'generated-session.json').open('w') as generated_log:
            run(['python3','tools/generate_vins_config.py','--output',str(out/'session'),
                 '--rig-config','config/hardware/rig.json'], stdout=generated_log)
        state['epoch'] = json.loads((out/'session/session.json').read_text())['epoch']
        save(state)
        if args.layer != 'perception':
            launch = 'hardware_mapping.launch.py' if args.layer == 'map' else 'hardware_plan.launch.py'
            spawn(state, 'map' if args.layer == 'map' else 'plan', ['bash','-c','source tools/hardware-env.bash; export FASTRTPS_DEFAULT_PROFILES_FILE="$PWD/config/hardware/vins_fastdds_udp_rxbuf4m.xml"; exec ros2 launch "tools/$1" "session_manifest:=$2"','_',launch,str(out/'session/session.json')],env)
        if args.layer in ('ev','control','full-load'):
            mode = 'compute_only' if args.layer=='full-load' else ('ev_only' if args.layer=='ev' else 'control')
            cfg = 'px4_bridge_ev.json' if mode=='ev_only' else 'px4_bridge_control.json'
            state['bridge_start_attempted'] = args.layer in ('ev','control')
            save(state)
            spawn(state,'bridge',['bash','-c','source tools/hardware-env.bash; export FASTRTPS_DEFAULT_PROFILES_FILE="$PWD/config/hardware/vins_fastdds_udp_rxbuf4m.xml"; exec ros2 run uav_px4_bridge px4_bridge --ros-args -p profile_path:="$PWD/config/hardware/px4_profile.json" -p frame_contract_path:="$PWD/config/components/px4_bridge/frames_vio_closed_loop.json" -p rig_config:="$PWD/config/hardware/rig.json" -p bridge_config_path:="$PWD/config/hardware/$1" -p runtime_mode:="$2" -p use_sim_time:=false','_',cfg,mode],env)
            state['px4_outputs'] = 'disabled' if mode=='compute_only' else mode; save(state)
        if args.measure_seconds is not None:
            spawn(state,'observer',['bash','-c','source tools/hardware-env.bash; export FASTRTPS_DEFAULT_PROFILES_FILE="$PWD/config/hardware/vins_fastdds_udp_rxbuf4m.xml"; exec python3 tools/diagnostics/record_hw09_load.py --output "$1" --duration "$2"','_',str(out/'observer'),str(args.measure_seconds)],env)
            deadline = time.monotonic()+60
            while not (out/'observer/ready').exists():
                if time.monotonic()>deadline: raise RuntimeError('Observer not ready')
                time.sleep(.2)
        # Finish Python/ROS imports before estimation becomes subject to freshness gates.
        if args.layer in ('full-load','ev','control'):
            deadline = time.monotonic()+60
            while args.layer=='full-load' and 'hardware compute-only ready' not in (out/'bridge.log').read_text():
                if time.monotonic()>deadline: raise RuntimeError('Bridge not ready')
                time.sleep(.2)
        if args.visuals:
            for channel in ('geometry','image'):
                deadline=time.monotonic()+90
                ready=out/('viz-'+channel+'-ready.json')
                while not ready.exists():
                    if time.monotonic()>deadline:raise RuntimeError('Visualization relay did not become ready: '+channel)
                    time.sleep(.2)
                relay=json.loads(ready.read_text())
                if relay['epoch']!=state['epoch'] or identity(relay['pid']) is None:
                    raise RuntimeError('Visualization relay identity does not match session')
                state['processes'].append({'name':'visuals-'+channel,'pid':relay['pid'],
                    'start_ticks':identity(relay['pid']),'log':str(out/('viz-'+channel+'-stats.json'))})
                save(state)
        run(['bash','tools/hardware-localization.sh','start',str(out/'session')],env=env)
        state['phase']='running'; save(state)
        print(json.dumps(state,indent=2))
    except BaseException as startup_error:
        state['phase']='cleanup_required'
        state['startup_error']=type(startup_error).__name__ + ': ' + str(startup_error)
        save(state)
        try:
            stop(state, startup_failure=True)
        except BaseException as cleanup_error:
            state['cleanup_error']=type(cleanup_error).__name__ + ': ' + str(cleanup_error)
            save(state)
            raise RuntimeError('Startup failed and owned resources need inspection; session state retained') from cleanup_error
        raise


if __name__ == '__main__':
    main()
