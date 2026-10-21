import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'project_root',
            default_value=os.environ.get('D435I_VINS_EGO_ROOT', ''),
            description='Repository root containing config/components/navigation/task_supervisor.json',
        ),
        Node(
            package='uav_navigation',
            executable='navigation_supervisor',
            name='uav_navigation',
            output='screen',
            parameters=[{'project_root': LaunchConfiguration('project_root')}],
        ),
    ])
