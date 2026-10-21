cmake_minimum_required(VERSION 3.8)
project(uav_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(action_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/LocalizationStatus.msg"
  "msg/DepthHealth.msg"
  "msg/MapStatus.msg"
  "msg/RGBDKeyframe.msg"
  "msg/PositionCommand.msg"
  "msg/NavigationCommand.msg"
  "msg/TrajectoryCancel.msg"
  "msg/Px4BridgeStatus.msg"
  "action/NavigateToPose.action"
  "srv/ResetMapping.srv"
  "srv/GetMapStatus.srv"
  "srv/GetOccupancySnapshot.srv"
  "srv/EnableOffboard.srv"
  DEPENDENCIES action_msgs std_msgs builtin_interfaces geometry_msgs sensor_msgs
)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
