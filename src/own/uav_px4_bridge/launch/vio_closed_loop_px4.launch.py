"""Attach the experimental VINS-only PX4 bridge to a running SITL stack."""
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uav_px4_bridge.vio_ego_bringup import bridge_position_command_remappings


def start(context):
    root = Path(LaunchConfiguration('project_root').perform(context)).resolve()
    sensor_config_arg = LaunchConfiguration('sensor_bridge_config').perform(context).strip()
    n08_mode = LaunchConfiguration('n08_mode').perform(context).lower()
    if n08_mode not in ('hold', 'compute_only', 'execute'):
        raise ValueError('n08_mode must be hold, compute_only, or execute')
    bridge_compute_only = n08_mode == 'compute_only'
    sensor_config = (Path(sensor_config_arg).resolve() if sensor_config_arg
                     else root / 'config/components/simulation/d435i_bridge.yaml')
    paths = {
        'profile_path': root / 'config/profiles/vio_closed_loop.json',
        'bridge_config_path': root / 'config/components/px4_bridge/vio_closed_loop.json',
        'frame_contract_path': root / 'config/components/px4_bridge/frames_vio_closed_loop.json',
    }
    for path in [sensor_config, *paths.values()]:
        if not path.is_file():
            raise FileNotFoundError(str(path))
    sensor_bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        name='d435i_sensor_bridge', output='screen',
        parameters=[{'config_file': str(sensor_config), 'use_sim_time': True}])
    node = Node(package='uav_px4_bridge', executable='px4_bridge',
                name='uav_px4_bridge', output='screen',
                parameters=[{key: str(value) for key, value in paths.items()},
                            {'use_sim_time': True}],
                remappings=bridge_position_command_remappings(bridge_compute_only))
    return [sensor_bridge, node]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('project_root', description='Absolute project source root'),
        DeclareLaunchArgument(
            'sensor_bridge_config', default_value='',
            description='Optional run-local Gazebo sensor bridge YAML; empty selects project default'),
        DeclareLaunchArgument(
            'n08_mode', default_value='execute',
            description='N08 comparison mode recorded in the run manifest: hold, compute_only, or execute'),
        OpaqueFunction(function=start),
    ])
