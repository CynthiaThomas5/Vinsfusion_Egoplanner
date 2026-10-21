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
    run = prepare_vio_ego_run(root, run_id, planner_config)
    planner = run['planner']
    ego_args = {key: _launch_arg(value)
                for key, value in run['ego_launch_arguments'].items()}

    bridge_share = Path(get_package_share_directory('uav_px4_bridge'))
    ego_share = Path(get_package_share_directory('ego_planner'))
    px4_stack = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(bridge_share / 'launch/vio_closed_loop_px4.launch.py')),
        launch_arguments={'project_root': str(root)}.items())
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
    depth_health = Node(
        package='uav_mapping', executable='depth_health_monitor',
        name='depth_health_monitor', output='screen',
        parameters=[{'project_root': str(root), 'use_sim_time': True}])
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

    print(f"VIO/EGO run artifacts: {run['run_directory']}")
    return [px4_stack, vins, localization, depth_health, mapping,
            ego, trajectory_server, navigation]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('project_root', description='Absolute repository root'),
        DeclareLaunchArgument('run_id', default_value='',
                              description='Optional unused artifacts/runs directory name'),
        DeclareLaunchArgument(
            'planner_config', default_value=DEFAULT_EGO_PLANNER_CONFIG,
            description='Project-relative JSON source for EGO planner parameters'),
        OpaqueFunction(function=start),
    ])
