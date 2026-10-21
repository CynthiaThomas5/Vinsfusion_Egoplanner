"""Bridge an existing PX4/Gazebo SITL model into the guarded debug truth path."""
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start(context):
    root = Path(LaunchConfiguration('project_root').perform(context)).resolve()
    profile_path = root / 'config/profiles/debug_truth.json'
    sensor_config = root / 'config/components/simulation/d435i_bridge.yaml'
    truth_config = root / 'config/components/simulation/debug_truth_bridge.yaml'
    if not profile_path.is_file() or not sensor_config.is_file() or not truth_config.is_file():
        raise FileNotFoundError('debug truth profile or bridge config is missing')
    sensor_bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        name='d435i_sensor_bridge',
        parameters=[{'config_file': str(sensor_config), 'use_sim_time': True}],
        output='screen')
    truth_bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        name='debug_truth_odometry_bridge',
        parameters=[{'config_file': str(truth_config), 'use_sim_time': True}],
        output='screen')
    adapter = Node(package='uav_sim', executable='debug_truth_adapter',
                   name='debug_truth_adapter',
                   parameters=[{'project_root': str(root), 'use_sim_time': True}],
                   output='screen')
    return [sensor_bridge, truth_bridge, adapter,
            RegisterEventHandler(OnProcessExit(target_action=sensor_bridge,
                on_exit=[EmitEvent(event=Shutdown(reason='D435i sensor bridge exited'))])),
            RegisterEventHandler(OnProcessExit(target_action=truth_bridge,
                on_exit=[EmitEvent(event=Shutdown(reason='Debug truth bridge exited'))])),
            RegisterEventHandler(OnProcessExit(target_action=adapter,
                on_exit=[EmitEvent(event=Shutdown(reason='Debug truth adapter exited'))]))]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('project_root', description='Absolute project source root'),
        OpaqueFunction(function=start),
    ])
