"""Attach the debug-only PX4 bridge to an already running PX4/Gazebo SITL."""
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start(context):
    root = Path(LaunchConfiguration('project_root').perform(context)).resolve()
    paths = {
        'profile_path': root / 'config/profiles/debug_truth.json',
        'bridge_config_path': root / 'config/components/px4_bridge/debug_truth.json',
        'frame_contract_path': root / 'config/components/px4_bridge/frames.json',
    }
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(str(path))
    node = Node(package='uav_px4_bridge', executable='px4_bridge',
                name='uav_px4_bridge', output='screen',
                parameters=[{key: str(value) for key, value in paths.items()},
                            {'use_sim_time': True}])
    return [node]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('project_root', description='Absolute project source root'),
        OpaqueFunction(function=start),
    ])
