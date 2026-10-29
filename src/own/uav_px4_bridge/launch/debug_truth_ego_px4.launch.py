"""Compose the debug-truth map, EGO, navigation and sole PX4 control path."""
import json
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from uav_sim.geometry import calibration


def start(context):
    root = Path(LaunchConfiguration('project_root').perform(context)).resolve()
    bridge_cfg = json.loads((root / 'config/components/px4_bridge/debug_truth.json').read_text())
    map_cfg = json.loads((root / 'config/components/mapping/ego_input.json').read_text())
    planner_cfg = json.loads((root / 'config/components/mapping/ego_planner.json').read_text())
    envelope_cfg = json.loads((root / 'config/components/navigation/vehicle_envelope.json').read_text())
    nav_cfg = json.loads((root / 'config/components/navigation/task_supervisor.json').read_text())
    frame_cfg = json.loads((root / 'config/components/px4_bridge/frames.json').read_text())
    rig = calibration(root / 'simulation/models/d435i/model.sdf')
    intrinsics = rig['cameras']['depth']['K']
    drone_id = str(planner_cfg['drone_id'])
    camera_pose_topic = map_cfg['ego_pose_topic']
    depth_topic = map_cfg['ego_depth_topic']
    camera_prefix = f'/drone_{drone_id}_'
    if (not camera_pose_topic.startswith(camera_prefix)
            or not depth_topic.startswith(camera_prefix)):
        raise ValueError('EGO input topics must match the configured single-drone id')
    if bridge_cfg['position_command_topic'] != frame_cfg['trajectory_input_topic']:
        raise ValueError('PX4 bridge and frame contract trajectory topics differ')

    map_adapter = Node(
        package='uav_mapping', executable='mapping_input_adapter',
        name='mapping_input_adapter', output='screen',
        parameters=[{'project_root': str(root), 'use_sim_time': True}],
        remappings=[
            (map_cfg['localization_status_topic'], bridge_cfg['debug_truth_status_topic']),
            (map_cfg['optimized_odometry_topic'], bridge_cfg['debug_truth_odometry_topic']),
        ])
    navigation = Node(
        package='uav_navigation', executable='navigation_supervisor',
        name='uav_navigation', output='screen',
        parameters=[{'project_root': str(root), 'use_sim_time': True}],
        remappings=[
            (nav_cfg['localization_status_topic'], bridge_cfg['debug_truth_status_topic']),
            (nav_cfg['odometry_topic'], bridge_cfg['debug_truth_odometry_topic']),
        ])

    ego_share = Path(get_package_share_directory('ego_planner'))
    ego_parameters = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(ego_share / 'launch/advanced_param.launch.py')),
        launch_arguments={
            'drone_id': drone_id,
            'map_size_x_': str(planner_cfg['map_size_m'][0]),
            'map_size_y_': str(planner_cfg['map_size_m'][1]),
            'map_size_z_': str(planner_cfg['map_size_m'][2]),
            'odometry_topic': bridge_cfg['debug_truth_odometry_topic'],
            'camera_pose_topic': camera_pose_topic.removeprefix(camera_prefix),
            'depth_topic': depth_topic.removeprefix(camera_prefix),
            'cloud_topic': 'cloud',
            'cx': str(intrinsics[2]), 'cy': str(intrinsics[5]),
            'fx': str(intrinsics[0]), 'fy': str(intrinsics[4]),
            'max_vel': str(planner_cfg['max_velocity_m_s']),
            'max_acc': str(planner_cfg['max_acceleration_m_s2']),
            'planning_horizon': str(planner_cfg['planning_horizon_m']),
            'odom_depth_timeout': str(planner_cfg['odom_depth_timeout_sim_s']),
            'obstacles_inflation': str(planner_cfg['obstacles_inflation_m']),
            'terminal_hold_neighborhood': str(envelope_cfg['map_policy']['terminal_hold_neighborhood_radius_m']),
            'ground_height': str(planner_cfg['ground_height_m']),
            'flight_type': str(planner_cfg['flight_type']),
            'point_num': '1',
            'point0_x': '0.0', 'point0_y': '0.0', 'point0_z': '0.0',
            'obj_num_set': str(planner_cfg['object_count']),
            'use_distinctive_trajs': str(planner_cfg['use_distinctive_trajectories']),
        }.items())
    trajectory_server = Node(
        package='ego_planner', executable='traj_server',
        name=f'drone_{drone_id}_traj_server', output='screen',
        remappings=[('planning/bspline', f'/drone_{drone_id}_planning/bspline')],
        parameters=[{'use_sim_time': True,
                     'traj_server/time_forward': planner_cfg['trajectory_time_forward_s']}])
    px4_bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(Path(get_package_share_directory('uav_px4_bridge')) /
                'launch/debug_truth_px4.launch.py')),
        launch_arguments={'project_root': str(root)}.items())
    return [map_adapter, ego_parameters, trajectory_server,
            navigation, px4_bridge]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('project_root', description='Absolute repository root'),
        OpaqueFunction(function=start),
    ])
