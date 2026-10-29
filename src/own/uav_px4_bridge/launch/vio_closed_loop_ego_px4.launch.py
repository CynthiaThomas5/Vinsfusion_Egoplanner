"""Launch the config-driven no-truth VINS, map, EGO and sole PX4 control path.

Gazebo with the PX4 x500+D435i model, PX4 SITL and the DDS Agent must already
be running. This launch starts the project's ROS-side sensor and navigation
stack and creates a fresh, immutable VINS session under artifacts/runs.
"""
import json
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from uav_px4_bridge.vio_ego_bringup import (
    DEFAULT_EGO_PLANNER_CONFIG,
    prepare_vio_ego_run,
)


def _launch_arg(value):
    return str(value).lower() if isinstance(value, bool) else str(value)


def start(context):
    root = Path(LaunchConfiguration('project_root').perform(context)).resolve()
    run_id = LaunchConfiguration('run_id').perform(context).strip()
    planner_config = LaunchConfiguration('planner_config').perform(context).strip()
    sensor_bridge_config = LaunchConfiguration('sensor_bridge_config').perform(context).strip()
    n08_mode = LaunchConfiguration('n08_mode').perform(context).lower()
    if n08_mode not in ('hold', 'compute_only', 'execute'):
        raise ValueError('n08_mode must be hold, compute_only, or execute')
    bridge_compute_only = n08_mode == 'compute_only'
    show_navigation = LaunchConfiguration('enable_visualization').perform(context).lower() in ('true', '1')
    run = prepare_vio_ego_run(root, run_id, planner_config)
    planner = run['planner']
    ego_args = {key: _launch_arg(value)
                for key, value in run['ego_launch_arguments'].items()}

    bridge_share = Path(get_package_share_directory('uav_px4_bridge'))
    ego_share = Path(get_package_share_directory('ego_planner'))
    px4_stack = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(bridge_share / 'launch/vio_closed_loop_px4.launch.py')),
        launch_arguments={'project_root': str(root),
                          'sensor_bridge_config': sensor_bridge_config,
                          'n08_mode': n08_mode}.items())
    vins = Node(
        package='vins', executable='vins_node', name='vins_estimator',
        namespace=run['session_namespace'], output='screen',
        arguments=[str(run['session_directory'] / 'vins.yaml')],
        parameters=[{'use_sim_time': True}],
        additional_env={'VINS_OPENCV_THREADS': str(json.loads((root / 'config/components/localization/vins_runtime.json').read_text())['opencv_threads'])})
    localization = Node(
        package='uav_localization', executable='localization_adapter',
        name='localization_adapter', output='screen',
        parameters=[{'project_root': str(root),
                     'session_manifest': str(run['session_manifest']),
                     'use_sim_time': True}])
    mapping = Node(
        package='uav_mapping', executable='mapping_input_adapter',
        name='mapping_input_adapter', output='screen',
        parameters=[{'project_root': str(root), 'use_sim_time': True}])
    ego = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(ego_share / 'launch/advanced_param.launch.py')),
        launch_arguments=ego_args.items())
    trajectory_server = Node(
        package='ego_planner', executable='traj_server',
        name=f"drone_{planner['drone_id']}_traj_server", output='screen',
        remappings=[('planning/bspline',
                     f"/drone_{planner['drone_id']}_planning/bspline")],
        parameters=[{'use_sim_time': True,
                     'traj_server/time_forward': planner['trajectory_time_forward_s']}])
    navigation = Node(
        package='uav_navigation', executable='navigation_supervisor',
        name='uav_navigation', output='screen',
        parameters=[{'project_root': str(root), 'use_sim_time': True}])

    mode_record = {
        'scope': 'N08 controlled comparison launch mode; this file is configuration evidence, not a flight or safety pass',
        'mode': n08_mode,
        'bridge_trajectory_input_topic': (
            '/n08/compute_only_position_cmd' if bridge_compute_only else '/position_cmd'),
        'ego_position_command_topic': '/position_cmd',
        'control_owner': 'uav_px4_bridge only',
        'ground_truth_online_allowed': False,
    }
    (run['run_directory'] / 'n08-runtime-mode.json').write_text(
        json.dumps(mode_record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"VIO/EGO run artifacts: {run['run_directory']}")
    nodes = [px4_stack, vins, localization, mapping,
             ego, trajectory_server, navigation]
    if show_navigation:
        nodes.append(Node(
            package='uav_navigation', executable='navigation_visualization',
            name='navigation_visualization', output='screen',
            parameters=[{'project_root': str(root),
                         'session_manifest': str(run['session_manifest']),
                         'use_sim_time': True}]))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('project_root', description='Absolute repository root'),
        DeclareLaunchArgument('run_id', default_value='',
                              description='Optional unused artifacts/runs directory name'),
        DeclareLaunchArgument(
            'planner_config', default_value=DEFAULT_EGO_PLANNER_CONFIG,
            description='Project-relative JSON source for EGO planner parameters'),
        DeclareLaunchArgument(
            'sensor_bridge_config', default_value='',
            description='Optional run-local Gazebo sensor bridge YAML for controlled sensor tests'),
        DeclareLaunchArgument(
            'n08_mode', default_value='execute',
            description='N08 comparison mode: hold, compute_only, or execute'),
        DeclareLaunchArgument(
            'enable_visualization', default_value='false',
            description='Read-only EGO curve, VINS path and session-bound RViz markers'),
        OpaqueFunction(function=start),
    ])
