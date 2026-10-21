# 单 D435i 传感器仿真

导航环境当前使用 [ego.sdf](../../../simulation/worlds/ego.sdf)，由 PX4 场景生成器接入，详见 [仿真资源](../../../simulation/README.md)。本页后续 `sensors.launch.py` 默认场景与 3 m 平面检查仍专用于静态相机标定，不是导航环境入口。

已实现 ament_python 包：启动 Gazebo 固定支架校准场景、GZ→ROS 单向桥、从 SDF 生成的固定 TF；另有单独的 `debug_truth.launch.py`，只连接已运行的 PX4/Gazebo SITL，并把调试真值适配到带新 epoch 的 `/debug_truth/*` 话题。真值节点不发布 PX4 控制，也不会启动 Gazebo 或 PX4。P3 控制状态机和飞行闭环仍未实现。

模型唯一来源为 simulation/models/d435i/model.sdf，640×480、87° 水平视场、50 mm 双目基线、200 Hz 相机 IMU，深度与左目共位，RGB 独立位于相机刚体中心。当前为理想无畸变、无噪声等效模型，不模拟真实红外纹理、主动投射、曝光或深度缺测，不能外推实机性能。

`uav_sim.geometry` 从 SDF 生成内参及 URDF。相机渲染坐标是 FLU，消息声明 optical frame，URDF 明确旋转到右／下／前。IMU 用 FLU。固定 TF 只包含 d435i_link 到各传感器，不伪造世界或机体运动 TF。

PX4 复合模型 `simulation/models/x500_d435i/model.sdf` 把唯一 D435i 固定安装在 x500 上，并由 Gazebo `OdometryPublisher` 向 `/debug_truth/base_odometry` 输出 `world`→`d435i_link` 真值。`d435i_bridge.yaml` 只桥接相机、IMU 和仿真时钟；`debug_truth_bridge.yaml` 单独桥接真值，且只由 `debug_truth.launch.py` 加载。VIO SITL launch 只加载传感器桥，不创建真值订阅。仿真 IMU 与 `d435i_link` 同位；debug adapter 为每次启动生成新 epoch，并将消息标为 `odom_<epoch>`→`d435i_imu_<epoch>`，源 stamp 原样保留。该 body frame 表示相机 IMU 原点，不是机体 `base_link`；PX4 原点／航向配对及相机到机体杆臂仍需单独配置和验证。

桥配置让相机、IMU 与真值输入桥按 ROS 订阅惰性激活；`/clock` 始终桥接。静态校准 run #19 已验证 31/31 项，并实际收到惰性桥接的数据。

Gazebo depth_camera 在本机 Harmonic 上将 CameraInfo 发布到默认 /sensors/d435i/camera_info；桥配置显式映射到 ROS /sensors/d435i/depth/camera_info。其余输入源 stamp 原样保留。

从项目根目录，在包含 Jazzy/Harmonic 与 ROS 图像桥的环境中：

```bash
source /opt/ros/jazzy/setup.bash
colcon build --base-paths src/own/uav_sim
source install/setup.bash
export GZ_PARTITION=d435i_sensor_calibration
export ROS_DOMAIN_ID=71
# 无 GPU 时可设置 LIBGL_ALWAYS_SOFTWARE=1；会降低渲染速度。
ros2 launch uav_sim sensors.launch.py project_root:="$PWD"
```

对 PX4 SITL x500_d435i 已在 Gazebo 中运行的情况，在单独终端启动调试桥（不要同时再启动 `sensors.launch.py`）：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch uav_sim debug_truth.launch.py project_root:="$PWD"
```

该入口只桥接配置中的传感器与真值输入，发布 `/debug_truth/optimized_imu_odom` 和 `/debug_truth/localization_status`。live SITL run #18 通过 10 条连续样本与 epoch/frame 检查；同次运行确认 Offboard、轨迹设定点、PX4 command 和外部视觉里程计输入均无 ROS 发布者。它不证明 PX4 EKF2 融合或飞行。

另一个相同 ROS_DOMAIN_ID 的终端执行：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
mkdir -p artifacts/runs/sensor-check
python3 tools/check_sensors.py --project-root "$PWD" --output artifacts/runs/sensor-check/report.json
```

校准检查仅适用于 sensor_calibration.sdf 的静态 3 m 平面与标记。检查双目视差／配对、CameraInfo、图像编码、深度单位、静态重力、时钟及固定 TF，报告实际接收频率。它不验证运动、VINS、飞行或最终定位质量。Ctrl-C 停止该 launch；子进程退出会结束该组合，不使用全局 pkill。
