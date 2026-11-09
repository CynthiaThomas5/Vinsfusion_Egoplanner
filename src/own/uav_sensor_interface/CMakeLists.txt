cmake_minimum_required(VERSION 3.5)
project(uav_sensor_interface)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(d435i_depth_to_meters_cpp src/depth_to_meters.cpp)
target_compile_features(d435i_depth_to_meters_cpp PUBLIC cxx_std_14)
ament_target_dependencies(d435i_depth_to_meters_cpp rclcpp sensor_msgs)

install(TARGETS d435i_depth_to_meters_cpp
  DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS scripts/hw02_sensor_capture
  DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
  PATTERN "__pycache__" EXCLUDE
  PATTERN "*.pyc" EXCLUDE)

ament_python_install_package(${PROJECT_NAME})
ament_package()
