"""Launch the calibration world, one-way sensor bridges and model-derived fixed TF."""
from pathlib import Path
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uav_sim.geometry import robot_description


def start(context):
    root = Path(LaunchConfiguration('project_root').perform(context)).resolve()
    model = root / 'simulation/models/d435i/model.sdf'
    description = robot_description(model)
    world_arg = LaunchConfiguration('world').perform(context)
    world = Path(world_arg).resolve() if world_arg else root / 'simulation/worlds/sensor_calibration.sdf'
    if not world.is_file():
        raise FileNotFoundError(world)
    gazebo = ExecuteProcess(cmd=['gz', 'sim', '-s', '-r', '--headless-rendering',
                                  str(world)],
                            additional_env={'GZ_SIM_RESOURCE_PATH': str(root / 'simulation/models') + ':' + os.environ.get('GZ_SIM_RESOURCE_PATH', '')},
                            output='screen')
    bridge = Node(package='ros_gz_bridge', executable='parameter_bridge', name='d435i_bridge',
                  parameters=[{'config_file': str(root / 'config/components/simulation/d435i_bridge.yaml'),
                               'use_sim_time': True}], output='screen')
    tf = Node(package='robot_state_publisher', executable='robot_state_publisher',
              parameters=[{'robot_description': description, 'use_sim_time': True}], output='screen')
    return [gazebo, bridge, tf, *[RegisterEventHandler(OnProcessExit(target_action=process,
                on_exit=[EmitEvent(event=Shutdown(reason='Sensor process exited'))])) for process in [gazebo, bridge, tf]]]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('project_root', description='Absolute project source root'),
                              DeclareLaunchArgument('world', default_value='', description='World SDF; empty selects static calibration'),
                              OpaqueFunction(function=start)])
