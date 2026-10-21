"""Resolve the no-truth VINS/EGO launch from the project's single config sources."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import uuid

DEFAULT_EGO_PLANNER_CONFIG = 'config/components/mapping/ego_planner.json'


def _read_json(root, relative):
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


def resolve_vio_ego_configuration(project_root, planner_config=DEFAULT_EGO_PLANNER_CONFIG):
    root = Path(project_root).resolve()
    planner_path = Path(planner_config)
    if planner_path.is_absolute():
        raise ValueError('Planner config must be relative to the project root')
    planner_config = planner_path.as_posix()
    planner_file = (root / planner_path).resolve()
    if not planner_file.is_relative_to(root):
        raise ValueError('Planner config must be inside the project root')
    profile = _read_json(root, 'config/profiles/vio_closed_loop.json')
    px4 = _read_json(root, 'config/components/px4_bridge/vio_closed_loop.json')
    frames = _read_json(root, 'config/components/px4_bridge/frames_vio_closed_loop.json')
    planner = _read_json(root, planner_config)
    mapping = _read_json(root, 'config/components/mapping/ego_input.json')
    navigation = _read_json(root, 'config/components/navigation/task_supervisor.json')
    vins_settings = _read_json(root, 'config/components/localization/vins_sim.json')

    if profile.get('name') != 'vio_closed_loop':
        raise ValueError('Expected the vio_closed_loop runtime profile')
    if any(profile.get(key) is not False for key in (
            'ground_truth_online_allowed', 'px4_debug_position_allowed',
            'gps_position_aiding_allowed')):
        raise ValueError('VIO profile permits a prohibited online position source')
    if (profile.get('mapping_localization') != 'vins'
            or profile.get('planner_localization') != 'vins'
            or profile.get('px4_position_source') != 'vins_external_odometry'):
        raise ValueError('VIO profile localization sources are inconsistent')
    if (px4.get('profile') != 'vio_closed_loop'
            or px4.get('localization_status_topic') != mapping.get('localization_status_topic')
            or px4.get('optimized_odometry_topic') != mapping.get('optimized_odometry_topic')):
        raise ValueError('PX4 and mapping localization inputs differ')
    if (navigation.get('localization_status_topic') != mapping.get('localization_status_topic')
            or navigation.get('odometry_topic') != mapping.get('optimized_odometry_topic')):
        raise ValueError('Navigation and mapping localization inputs differ')
    if (frames.get('profile') != 'vio_closed_loop'
            or frames.get('ground_truth_online_allowed') is not False
            or frames.get('gps_position_aiding_allowed') is not False
            or not str(frames.get('trajectory_input_topic', '')).startswith('/')):
        raise ValueError('VIO frame contract is incomplete or allows prohibited aiding')
    if (vins_settings.get('imu') != 1 or vins_settings.get('num_of_cam') != 2
            or vins_settings.get('estimate_extrinsic') != 0):
        raise ValueError('VIO EGO launch requires fixed-extrinsic stereo plus IMU')

    drone_id = planner.get('drone_id')
    if type(drone_id) is not int or drone_id < 0 or mapping.get('ego_drone_id') != drone_id:
        raise ValueError('EGO planner and mapping drone ids differ')
    obstacles_inflation = planner.get('obstacles_inflation_m')
    if (type(obstacles_inflation) not in (int, float)
            or not math.isfinite(obstacles_inflation) or obstacles_inflation < 0):
        raise ValueError('obstacles_inflation_m must be a finite non-negative number')
    prefix = f'/drone_{drone_id}_'
    topics = {
        'camera_pose': mapping.get('ego_pose_topic', ''),
        'depth': mapping.get('ego_depth_topic', ''),
    }
    for name, topic in topics.items():
        if not topic.startswith(prefix) or topic == prefix:
            raise ValueError(f'EGO {name} topic must match drone id {drone_id}')

    sim_model = root / 'simulation/models/d435i/model.sdf'
    if not sim_model.is_file():
        raise FileNotFoundError(sim_model)
    # Import the model reader from the project's source package so launch-time
    # intrinsics always come from the same SDF used to generate VINS calibration.
    sim_source = str(root / 'src/own/uav_sim')
    if sim_source not in sys.path:
        sys.path.insert(0, sim_source)
    from uav_sim.geometry import calibration

    rig = calibration(sim_model)
    k = rig['cameras']['depth']['K']
    relative_topics = {name: topic.removeprefix(prefix) for name, topic in topics.items()}
    startup_waypoint = planner.get('startup_waypoint_enu_m', [0.0, 0.0, 0.0])
    if (not isinstance(startup_waypoint, list) or len(startup_waypoint) != 3
            or not all(isinstance(value, (int, float)) and math.isfinite(value)
                       for value in startup_waypoint)):
        raise ValueError('startup_waypoint_enu_m must contain x, y and z')

    ego_arguments = {
        'drone_id': drone_id,
        'map_size_x_': planner['map_size_m'][0],
        'map_size_y_': planner['map_size_m'][1],
        'map_size_z_': planner['map_size_m'][2],
        'odometry_topic': mapping['ego_odometry_topic'],
        'camera_pose_topic': relative_topics['camera_pose'],
        'depth_topic': relative_topics['depth'],
        'cloud_topic': 'cloud',
        'cx': k[2], 'cy': k[5], 'fx': k[0], 'fy': k[4],
        'max_vel': planner['max_velocity_m_s'],
        'max_acc': planner['max_acceleration_m_s2'],
        'planning_horizon': planner['planning_horizon_m'],
        'odom_depth_timeout': planner['odom_depth_timeout_sim_s'],
        'obstacles_inflation': obstacles_inflation,
        'ground_height': planner['ground_height_m'],
        'flight_type': planner['flight_type'],
        'point_num': 1,
        'point0_x': startup_waypoint[0],
        'point0_y': startup_waypoint[1],
        'point0_z': startup_waypoint[2],
        'obj_num_set': planner['object_count'],
        'use_distinctive_trajs': planner['use_distinctive_trajectories'],
    }
    source_files = [
        'config/profiles/vio_closed_loop.json',
        'config/components/simulation/d435i_bridge.yaml',
        'config/components/localization/vins_sim.json',
        'config/components/localization/health.json',
        'config/components/mapping/ego_input.json',
        planner_config,
        'config/components/navigation/task_supervisor.json',
        'config/components/px4_bridge/vio_closed_loop.json',
        'config/components/px4_bridge/frames_vio_closed_loop.json',
        'simulation/models/d435i/model.sdf',
    ]
    return {
        'project_root': root,
        'profile': profile,
        'planner': planner,
        'planner_config': planner_config,
        'mapping': mapping,
        'navigation': navigation,
        'rig': rig,
        'ego_launch_arguments': ego_arguments,
        'source_files': source_files,
    }


def prepare_vio_ego_run(project_root, run_id='', planner_config=DEFAULT_EGO_PLANNER_CONFIG):
    root = Path(project_root).resolve()
    resolved = resolve_vio_ego_configuration(root, planner_config)
    if not run_id:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        run_id = f'vio-ego-sitl-{stamp}-{uuid.uuid4().hex[:8]}'
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{2,95}', run_id):
        raise ValueError('run_id must be a simple path component')

    run_dir = root / 'artifacts/runs' / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    session_dir = run_dir / 'session'
    tools_dir = str(root / 'tools')
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from generate_vins_config import generate

    session = generate(root, session_dir)
    source_hashes = {}
    for relative in resolved['source_files']:
        data = (root / relative).read_bytes()
        source_hashes[relative] = hashlib.sha256(data).hexdigest()
    manifest = {
        'run_id': run_id,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'qualification': 'PROVISIONAL no-truth VIO/EGO SITL bringup; launch does not imply flight acceptance',
        'profile': 'vio_closed_loop',
        'planner_config': resolved['planner_config'],
        'source_sha256': source_hashes,
        'model_sha256': resolved['rig']['model_sha256'],
        'session_manifest': str(session_dir / 'session.json'),
        'session': session,
        'ego_launch_arguments': resolved['ego_launch_arguments'],
    }
    (run_dir / 'launch-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return {
        'run_id': run_id,
        'run_directory': run_dir,
        'session_directory': session_dir,
        'session_manifest': session_dir / 'session.json',
        'session_namespace': session['namespace'],
        'ego_launch_arguments': resolved['ego_launch_arguments'],
        'planner': resolved['planner'],
    }
