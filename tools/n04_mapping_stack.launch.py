"""Launch real sensor, VINS, mapping and plan_env components with no PX4 path."""
import json
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription,
                            OpaqueFunction, RegisterEventHandler)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from uav_px4_bridge.vio_ego_bringup import (
    DEFAULT_EGO_PLANNER_CONFIG,
    prepare_vio_ego_run,
)


def _launch_value(value):
    return str(value).lower() if isinstance(value, bool) else str(value)


def start(context):
    root = Path(LaunchConfiguration('project_root').perform(context)).resolve()
    world = Path(LaunchConfiguration('world').perform(context)).resolve()
    run_id = LaunchConfiguration('run_id').perform(context).strip()
    planner_config = LaunchConfiguration('planner_config').perform(context).strip()
    if not world.is_file():
        raise FileNotFoundError(world)
    run = prepare_vio_ego_run(root, run_id, planner_config)
    arguments = {key: _launch_value(value)
                 for key, value in run['ego_launch_arguments'].items()}

    sim_share = Path(get_package_share_directory('uav_sim'))
    ego_share = Path(get_package_share_directory('ego_planner'))
    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(sim_share/'launch/sensors.launch.py')),
        launch_arguments={'project_root': str(root), 'world': str(world)}.items())
    vins = Node(
        package='vins', executable='vins_node', name='vins_estimator',
        namespace=run['session_namespace'], output='screen',
        arguments=[str(run['session_directory']/'vins.yaml')],
        parameters=[{'use_sim_time': True}],
        additional_env={
            'VINS_OPENCV_THREADS': str(json.loads(
                (root/'config/components/localization/vins_runtime.json').read_text()
            )['opencv_threads'])
        })
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
        PythonLaunchDescriptionSource(str(ego_share/'launch/advanced_param.launch.py')),
        launch_arguments=arguments.items())

    critical = [vins, localization, depth_health, mapping]
    shutdown_handlers = [
        RegisterEventHandler(OnProcessExit(
            target_action=action,
            on_exit=[EmitEvent(event=Shutdown(reason='N04 mapping component exited'))]))
        for action in critical
    ]
    return [sensors, *critical, ego, *shutdown_handlers]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('project_root', description='Project root'),
        DeclareLaunchArgument('world', description='Generated N04 diagnostic sensor world'),
        DeclareLaunchArgument('run_id', description='Fresh launch/session artifact id'),
        DeclareLaunchArgument('planner_config', default_value=DEFAULT_EGO_PLANNER_CONFIG),
        OpaqueFunction(function=start),
    ])
