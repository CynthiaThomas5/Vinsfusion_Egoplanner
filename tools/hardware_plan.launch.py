"""HW06 calculation only: existing real map, EGO, traj_server and action; no PX4 bridge."""
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    root = Path(__file__).resolve().parents[1]
    return LaunchDescription([
        DeclareLaunchArgument('session_manifest'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(root / 'tools/hardware_mapping.launch.py')),
            launch_arguments={'project_root': str(root), 'compute_plan': 'true',
                              'session_manifest': LaunchConfiguration('session_manifest')}.items()),
    ])
