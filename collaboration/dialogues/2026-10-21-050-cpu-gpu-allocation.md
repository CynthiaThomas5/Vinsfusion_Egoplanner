# CPU／GPU使用情况与迁移可行性

用户询问当前是否均用CPU、能否改用GPU。核对实际运行与源码：Gazebo渲染／传感器成像和RViz已使用RTX3060；VINS、EGO地图／规划、PX4和ROS状态逻辑主要CPU。VINS具备CUDA前端源码，但当前GPU_MODE未启用、OpenCV无CUDA、Ceres_NO_CUDA、无nvcc，不能只开参数。GPU前端迁移是候选方向，尚未实施或宣称解决停顿。用户此前要求持续至16m目标到达仍有效，继续定位阻塞及导航验证。
