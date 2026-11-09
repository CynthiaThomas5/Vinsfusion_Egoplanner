import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node, SetRemap
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    camera_share = get_package_share_directory('realsense2_camera')
    adapter_share = get_package_share_directory('uav_sensor_interface')
    camera_launch = os.path.join(camera_share, 'launch', 'rs_launch.py')
    camera_config = os.path.join(adapter_share, 'config', 'd435i_camera.yaml')

    camera_arguments = {
        'camera_name': 'camera_b',
        'serial_no': [TextSubstitution(text='_'), LaunchConfiguration('serial_no')],
        'config_file': "'{}'".format(camera_config),
        'enable_depth': 'true',
        'enable_color': LaunchConfiguration('enable_color'),
        'depth_width': '640',
        'depth_height': '480',
        'depth_fps': '15.0',
        'color_width': '640',
        'color_height': '480',
        'color_fps': '15.0',
        'infra_width': '640',
        'infra_height': '480',
        'infra_fps': '15.0',
        'infra_qos': 'SENSOR_DATA',
        'enable_gyro': 'true',
        'gyro_fps': '200.0',
        'enable_accel': 'true',
        'accel_fps': '100.0',
        'enable_fisheye1': 'false',
        'enable_fisheye2': 'false',
        'enable_confidence': 'false',
        'enable_pointcloud': 'false',
        'align_depth': 'false',
        'enable_sync': 'false',
        'depth_qos': 'SENSOR_DATA',
        'color_qos': 'SENSOR_DATA',
    }

    camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(camera_launch),
        launch_arguments=camera_arguments.items(),
    )

    camera_topics = GroupAction(
        scoped=True,
        actions=[
            SetRemap('/camera_b/infra1/image_rect_raw', '/sensors/d435i/infra1/image_rect_raw'),
            SetRemap('/camera_b/infra1/camera_info', '/sensors/d435i/infra1/camera_info'),
            SetRemap('/camera_b/infra2/image_rect_raw', '/sensors/d435i/infra2/image_rect_raw'),
            SetRemap('/camera_b/infra2/camera_info', '/sensors/d435i/infra2/camera_info'),
            SetRemap('/camera_b/depth/image_rect_raw', '/sensors/d435i/depth/image_rect_raw'),
            SetRemap('/camera_b/depth/camera_info', '/sensors/d435i/depth/camera_info'),
            SetRemap('/camera_b/imu', '/sensors/d435i/imu'),
            SetRemap('/camera_b/color/image_raw', '/sensors/d435i/color/image_raw'),
            SetRemap('/camera_b/color/camera_info', '/sensors/d435i/color/camera_info'),
            camera,
        ],
    )

    depth_adapter = Node(
        package='uav_sensor_interface',
        executable='d435i_depth_to_meters_cpp',
        name='d435i_depth_to_meters',
        namespace='/sensors/d435i',
        parameters=[{
            'input_topic': '/sensors/d435i/depth/image_rect_raw',
            'output_topic': '/sensors/d435i/depth',
            'meters_per_unit': 0.001,
            'max_output_rate_hz': ParameterValue(
                LaunchConfiguration('depth_output_rate_hz'), value_type=float),
        }],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('serial_no', description='Required D435i API serial from hardware rig identity'),
        DeclareLaunchArgument('depth_output_rate_hz', default_value='0.0',
                              description='Metric depth output cap; zero keeps every native frame'),
        DeclareLaunchArgument(
            'enable_color',
            default_value='false',
            description='Enable RGB only when this session needs visual keyframes.',
        ),
        camera_topics,
        depth_adapter,
    ])
