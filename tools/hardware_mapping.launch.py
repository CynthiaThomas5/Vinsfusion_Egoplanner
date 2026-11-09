"""Ground-only real-depth mapping; sensor and localization owners run separately."""
import json
import hashlib
from pathlib import Path
import re

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start(context):
    plan = LaunchConfiguration('compute_plan').perform(context) == 'true'
    for process in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            argv = process.read_bytes().decode(errors='replace').split('\0')
        except (OSError, ProcessLookupError):
            continue
        if any(Path(arg).name in ('ego_planner_node', 'mapping_input_adapter', 'traj_server', 'navigation_supervisor', 'px4_bridge', 'px4_bridge_node') for arg in argv[:2]):
            raise RuntimeError('A map owner or mapping adapter is already running')
    root = Path(LaunchConfiguration('project_root').perform(context)).resolve()
    manifest = Path(LaunchConfiguration('session_manifest').perform(context)).resolve()
    session = json.loads(manifest.read_text())
    if (session.get('rig_config') != 'config/hardware/rig.json'
            or not re.fullmatch('[0-9a-f]{32}', session.get('epoch', ''))):
        raise ValueError('A real hardware session manifest is required')
    from uav_sim.geometry import load_session_rig
    rig = load_session_rig(root, session)
    config = json.loads((root / 'config/hardware/mapping.json').read_text())
    params = dict(config['parameters'])
    if params.get('use_sim_time') is not False or params.get('fsm/flight_type') != 1:
        raise ValueError('Ground mapping requires system time and manual targets')
    if plan:
        lock = json.loads((root / 'dependencies/sources.json').read_text())
        source = next(item for item in lock['sources'] if item['id'] == 'ego_planner')
        for relative, expected in source['patched_files_sha256'].items():
            path = root / source['target'] / (relative[4:] if relative.startswith('src/') else relative)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise RuntimeError('EGO source differs from lock: ' + str(path))
        from uav_navigation import node as navigation_node
        if Path(navigation_node.__file__).read_bytes() != (
                root / 'src/own/uav_navigation/uav_navigation/node.py').read_bytes():
            raise RuntimeError('Installed navigation differs from source; rebuild with fresh build directory')
        params.update(json.loads((root / 'config/hardware/planner.json').read_text())['parameters'])
    k = rig['cameras']['depth']['K']
    params.update({'grid_map/fx': k[0], 'grid_map/fy': k[4],
                   'grid_map/cx': k[2], 'grid_map/cy': k[5]})
    policy = json.loads((root / 'config/hardware/mapping_input.json').read_text())
    mapper = Node(
        package='ego_planner', executable='ego_planner_node', name='hardware_map_owner',
        output='screen', parameters=[params], remappings=[
            ('odom_world', policy['optimized_odometry_topic']),
            ('grid_map/odom', policy['optimized_odometry_topic']),
            ('grid_map/depth', policy['ego_depth_topic']),
            ('grid_map/pose', policy['ego_pose_topic']),
            ('grid_map/cloud', '/hardware_map_only/unused_cloud'),
            ('/move_base_simple/goal', '/hardware_map_only/unused_goal'),
            ('/navigation/ego_goal', '/navigation/ego_goal' if plan else '/hardware_map_only/unused_navigation_goal'),
            ('planning/bspline', '/planning/bspline' if plan else '/hardware_map_only/bspline'),
            ('grid_map/occupancy_inflate', '/hardware_map_only/occupancy_inflate')])
    adapter = Node(
        package='uav_mapping', executable='mapping_input_adapter',
        name='mapping_input_adapter', output='screen', parameters=[{
            'project_root': str(root), 'session_manifest': str(manifest),
            'policy_config': 'config/hardware/mapping_input.json',
            'use_sim_time': False}])
    nodes = [mapper, adapter]
    if plan:
        nodes.extend([
            Node(package='ego_planner', executable='traj_server', name='traj_server',
                 output='screen', parameters=[{'use_sim_time': False, 'traj_server/time_forward': 1.0}],
                 remappings=[('planning/bspline', '/planning/bspline')]),
            Node(package='uav_navigation', executable='navigation_supervisor',
                 name='uav_navigation', output='screen', parameters=[{
                     'project_root': str(root), 'supervisor_config': 'config/hardware/task_supervisor.json',
                     'use_sim_time': False}]),
        ])
    handlers = [RegisterEventHandler(OnProcessExit(
        target_action=node, on_exit=[EmitEvent(event=Shutdown(
            reason='Hardware mapping component exited'))])) for node in nodes]
    return [*nodes, *handlers]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('compute_plan', default_value='false', choices=['false', 'true']),
        DeclareLaunchArgument('project_root', default_value=str(Path(__file__).resolve().parents[1])),
        DeclareLaunchArgument('session_manifest', description='Current real VINS session.json'),
        OpaqueFunction(function=start),
    ])
