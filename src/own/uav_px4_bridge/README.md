# uav_px4_bridge

该包是 PX4 Offboard 的唯一 ROS 控制出口。`debug_truth` profile 支撑 P3 调试；实验性 `vio_closed_loop` profile 只接入 VINS 定位状态和外部里程计，配置见 `config/components/px4_bridge/vio_closed_loop.json` 与 `frames_vio_closed_loop.json`。它引用单一共享 PX4 控制参数文件；profile 文件只保存各自的定位输入和 VIO 方差。两个 profile 都必须显式调用 `/uav_px4_bridge/enable_offboard`，并通过定位、EKF2 EV 融合、无 GNSS、时钟与 PX4 状态门控后才发布控制；默认状态为禁用。节点消费 epoch 专属定位状态、外部里程计、PX4 状态／TimesyncStatus，以及 EGO `PositionCommand`，独占发布 `/fmu/in/vehicle_visual_odometry`、`/fmu/in/offboard_control_mode`、`/fmu/in/trajectory_setpoint` 和 `/fmu/in/vehicle_command`。定位适配器和评估节点不发布控制。

`debug_truth` 输入 `/debug_truth/optimized_imu_odom` 来自 Gazebo `world`→`d435i_link` 真值适配器，输出 frame 为 `odom_<epoch>`→`d435i_imu_<epoch>`。这代表相机 IMU 原点，不代表机体 `base_link`。PX4 原点／航向与杆臂配对由 SDF 导出的配置明确提供，需由运行时配对健康门控；真值组合只用于调试，不可作为最终视觉验收。所有设定点与 OffboardControlMode 由本包状态机管理。

`vio_closed_loop` 使用 `/localization/status`、`/localization/optimized_imu_odom` 和 `/clock`，launch 同时加载只桥接 D435i 传感器与时钟的 Gazebo bridge，不会订阅 debug_truth 位姿或完整世界地图。PX4 SITL 使用 autostart ID 5011；可用 `python3 tools/stage_px4_debug_params.py --profile vio_closed_loop --px4-build <run-local-px4-build>` 在隔离的运行副本生成 airframe overlay，再用 `ros2 launch uav_px4_bridge vio_closed_loop_px4.launch.py project_root:=/workspace` 接入已运行的 VINS/PX4 SITL。当前 profile 仍为 `runtime_ready=false`，VIO 方差、时间门槛与 EKF2 融合尚未用 ULog 和飞行验证，不能视为 P5 通过。

`ros2 launch uav_px4_bridge vio_closed_loop_ego_px4.launch.py project_root:=/workspace` 是完整 ROS 侧 VIO/EGO bringup：它要求 Gazebo x500+D435i、PX4 SITL 与 DDS Agent 已运行，然后按当前项目配置启动传感器 bridge、生成全新 VINS session、VINS、定位健康适配器、深度健康与建图适配器、EGO、轨迹服务器、导航监督器和唯一 PX4 bridge。EGO 深度相机内参从 `simulation/models/d435i/model.sdf` 读取；运行配置、哈希和 VINS session 写到唯一的 `artifacts/runs/<run_id>`。重复指定已存在的 run_id 会失败。该入口已在固定 Jazzy 新目录构建，并于 #171 首次用于真实 SITL；稳定门、目标派发与安全降落均有记录，但动作仍因定位 normalized_cost 超限而失败。profile 仍是 `runtime_ready=false`，VIO 精度、重复目标与长时避障未验收；启动成功不代表 Goal/P5 通过。

闭环 launch 默认读取 `config/components/mapping/ego_planner.json`；可通过 `planner_config:=<project-relative-json>` 选择项目内另一份 EGO 参数源。实际路径及哈希随每次 VINS session 写入 launch manifest。当前经验证的 CPU 参数直接保存在默认配置中；旧低动态诊断副本已归档，见 `dependencies/retired-code-20261021.json`。

ENU `PositionCommand` 到 PX4 NED 的转换要求 READY、匹配 epoch/frame/goal 与有限数值。外部里程计时间戳经仿真时钟、单调时钟和 PX4 `TimesyncStatus.estimated_offset` 映射；拒绝过期或回退时钟、陈旧同步和错误坐标。`debug_truth` PX4 参数关闭 PX4 GazeboBridge 重复真值 odometry（`SIM_GZ_EN_ODOM=0`），EKF2 使用 EV 且关闭 GPS aiding。

P3 #34 已完成 debug_truth 深度建图→EGO action/READY轨迹→PX4 Offboard 目标飞行闭环：plan_env 峰值2,047点，938条匹配 goal_id/epoch 的 READY 命令，目标动作以 position+yaw dwell 成功，PX4 随后降落并解除武装。PX4 ULog确认808条外部视觉里程计和 EKF2 EV aid 融合；GPS EKF控制关闭且无 GNSS aiding。P3 阶段据此通过；该 run 没有专门放置障碍，不能证明避障净空，也不代表最终视觉无真值 profile。完整数据和 SHA-256 见 [`p3-px4-ego-flight.json`](../../../progress/evidence/p3-px4-ego-flight.json) 与 [`p3-stage-exit-audit.json`](../../../progress/evidence/p3-stage-exit-audit.json)。

回归命令：`python3 tools/test_px4_bridge_control.py`、`python3 tools/test_px4_bridge_frames.py`、`python3 tools/test_px4_bridge_time_mapping.py`、`python3 tools/test_px4_debug_params.py`、`python3 tools/test_px4_bridge_vio_profile.py`；Jazzy 节点加载探针为 `tools/probe_px4_bridge_profile_load.py`。

HW08 的硬件候选由同一节点加载 `config/hardware/px4_profile.json`、`px4_bridge_ev.json` 和 `rig.json`。`runtime_mode=ev_only` 不创建三个 PX4 控制发布者或启用服务，也不订阅 `/clock`、加载 SDF；硬件 `control` 使用 `px4_bridge_control.json`，复用相同OffboardSupervisor和显式使能服务；未通过安装准入的真实rig仍拒绝加载。EV 使用任意初始航向的 `POSE_FRAME_FRD`、BODY_FRD 速度；系统 epoch 的原始 source stamp 直接作为 timestamp_sample，发送时间独立记录，不重复补偿 DDS offset。

```bash
source tools/hardware-env.bash
ros2 run uav_px4_bridge px4_bridge --ros-args \
  -p profile_path:="$PWD/config/hardware/px4_profile.json" \
  -p bridge_config_path:="$PWD/config/hardware/px4_bridge_ev.json" \
  -p frame_contract_path:="$PWD/config/components/px4_bridge/frames_vio_closed_loop.json" \
  -p rig_config:="$PWD/config/hardware/rig.json"
```

当前真实安装仍为 UNMEASURED，上述入口只报告门控状态、输出0 EV；用户已确认板上IMU芯片平移为FRD(0.20,0.01,0)m，完整安装旋转仍待验证。HW08整体未通过，详见[软件/安装审计](../../../progress/evidence/hw08-body-time-20261103.md)。定向检查为 `python3 tools/test_hw08_transforms_time.py`；真实融合与飞行未测。

硬件control的局部配准先把完整IMU姿态转换为body姿态，再对齐任意初始yaw/原点，避免将光学IMU的右轴当机头。PX4同步消息已在Agent系统epoch中，硬件遥测不重复加offset；分别保留源龄和单调接收龄。现有规划PositionCommand只给yaw/yaw_dot，杆臂转换仍是低倾角候选，完整加速度等价尚未资格化。原控制器目前发布位置/yaw设定点。隔离节点检查：`ROS_DOMAIN_ID=83 python3 tools/test_hw08_control_node.py`，合成安装配置仅用于测试；不连接Agent或真实PX4。

板上柔性底板的近似数值保存在rig的`bench_observation.approximate_transform`，未提升为`T_airframe_imu`。用户接受板上近似交付，严格刚性检验未通过；当前真实rig仍阻止EV和control输出。详细残差与增加订阅后的时效失败见[板上证据](../../../progress/evidence/hw08-board-20261103.md)。
