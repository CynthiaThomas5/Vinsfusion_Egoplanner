# VINS 仿真调试（P2 尚未完整验收）

本页为 P2 开发操作，不是完整飞行启动说明。已验证静置初始化、一次物理台架动态运行和一次真实输入回放中的定位适配。健康参数仍是初期调试护栏，重复校准、完整故障注入和飞机安装外参尚未完成；不要连接控制出口。

在项目根目录的 Jazzy 环境中加载已构建包并生成全新会话。构建目录按每次运行单独指定；以下路径示例对应已有开发构建：

```bash
source /opt/ros/jazzy/setup.bash
source artifacts/runs/p2-build-20261016/install/setup.bash
source artifacts/runs/p2-localization-adapter-replay-20261016-05/install/setup.bash
python3 tools/generate_vins_config.py --output "$PWD/artifacts/runs/my-vins-test/session"
```

内参和相对 IMU 外参来自唯一 SDF，配置哈希及 epoch 在 session.json。输出目录必须不存在。非几何参数在 config/components/localization/vins_sim.json；当前理想无噪声模型仍使用正的求解协方差权重，未做真实相机噪声标定。

相同 ROS_DOMAIN_ID 的终端分别启动传感器、VINS 与定位适配器：

```bash
source /opt/ros/jazzy/setup.bash
source artifacts/runs/p2-build-20261016/install/setup.bash
source artifacts/runs/p2-localization-adapter-replay-20261016-05/install/setup.bash
export ROS_DOMAIN_ID=75
export GZ_PARTITION=d435i_vins_debug
ros2 launch uav_sim sensors.launch.py project_root:="$PWD"
```

```bash
source /opt/ros/jazzy/setup.bash
source artifacts/runs/p2-build-20261016/install/setup.bash
source artifacts/runs/p2-localization-adapter-replay-20261016-05/install/setup.bash
export ROS_DOMAIN_ID=75
VINS_DEBUG_NS=$(python3 -c 'import json; print(json.load(open("artifacts/runs/my-vins-test/session/session.json"))["namespace"])')
ros2 run vins vins_node "$PWD/artifacts/runs/my-vins-test/session/vins.yaml" --ros-args -p use_sim_time:=true -r __ns:="$VINS_DEBUG_NS"
```

在另一个终端启动适配器：

```bash
source /opt/ros/jazzy/setup.bash
source artifacts/runs/p2-build-20261016/install/setup.bash
source artifacts/runs/p2-localization-adapter-replay-20261016-05/install/setup.bash
export ROS_DOMAIN_ID=75
ros2 run uav_localization localization_adapter --ros-args \
  -p project_root:="$PWD" \
  -p session_manifest:="$PWD/artifacts/runs/my-vins-test/session/session.json"
```

查看状态和输出：

```bash
ros2 topic echo /localization/status
ros2 topic hz /localization/optimized_imu_odom
ros2 topic hz /localization/imu_odom
```

只有 `valid: true`／`state: TRACKING` 时才发布新适配里程计。
深度输入健康门单独运行，不参与 VINS 定位状态：`ros2 run uav_mapping depth_health_monitor --ros-args -p project_root:="$PWD"`，查看 `ros2 topic echo /mapping/depth_health`。`READY` 仅表示深度消息 frame／编码／尺寸／步长／数据长度匹配且在 1.0 秒稳态墙钟阈值内有新帧；该阈值为 PROVISIONAL，状态不证明像素有效或地图可用。深度源时间回退会锁定到监视进程重启。
优化输出约 15 Hz，IMU 传播输出约 200 Hz；Odometry 保留源 stamp，frame 为该 epoch 的 `odom_<epoch>` 和 `d435i_imu_<epoch>`。优化里程计使用 reliable QoS（EGO 订阅端要求 reliable），IMU 传播里程计使用 sensor-data best-effort QoS。`covariance_valid` 当前为 false，上游没有估计协方差。适配器不发布 TF、`base_link`、PX4 消息或控制指令。

适配器校验 session manifest、配置哈希、时钟、双目／IMU／遥测／优化／传播数据的新鲜度，要求优化状态与遥测时间匹配，并检查三个 VINS 输出端点属于同一 ROS 节点。接收年龄按观察到的 ROS 时钟速率折算为仿真时间，源时间年龄仍独立限制；时钟停滞使用稳态墙钟检测。发生时间回退、数据过期、端点更换或初始化超时后状态锁存为 LOST/LOCKED；必须停止本次会话并生成新 session/epoch，不能复用 `.localization-used` 标记已存在的目录。当前尚未验证 VINS 内部 switch topic 的运行时切换，不要通过 `/vins_cam_switch`、`/vins_imu_switch` 或 `/vins_restart` 延续同一适配会话。

回放包含录制的 `/clock` 时，不要同时传给 `ros2 bag play` 的 `--clock` 选项；该选项会从录包时间戳重新生成时钟，和消息内仿真时间不一致。可用 `tools/fault_relay.py` 对双目、IMU 或深度输入按消息 header stamp 做可重复断流，输入经 `/fault/input/...` 重映射，消费者继续订阅唯一正式传感器话题。故障窗口报告记录各输入实际丢弃和恢复转发的 stamp；探针记录状态转换的 ROS 时钟与墙钟。深度 relay 可重复注入；建图适配器现在消费深度健康状态，并在失效时请求清图。现有两次深度断流回放只验证健康状态门，合成集成 smoke 验证定位失效清图；仍需把真实深度断流接入 plan_env 并验证规划器停止使用旧地图。

只读原始 VINS 探针（相同 ROS_DOMAIN_ID）：

```bash
python3 tools/probe_vins.py --session artifacts/runs/my-vins-test/session/session.json --output artifacts/runs/my-vins-test/probe --seconds 30
```

每次重启 VINS 都重新生成会话和 epoch，禁止用旧配置延续旧地图。TRACKING 表示通过当前 P2 调试门槛，不是最终精度或可飞证明。建图输入适配器和 EGO `plan_env` 已通过合成 ROS smoke 验证定位无效时清图；动态 run #08 观察到同 stamp 输入和变化中的占据点，单墙几何残差中位数 3.63 cm、P95 7.31 cm，点云时间戳使用仿真 `/clock`。这是一次探索性对照，不是地图验收。后续 run 已验证 reliable 优化里程计可被 EGO 接收；EGO 离开 INIT 并进入规划，但多数轨迹尝试失败，仅一次成功。另一次停机诊断中 EGO 收到 SIGINT／SIGTERM 后仍未退出。稳定规划、优雅停机、地图 stale／epoch 故障响应尚未验证。Jazzy DDS 首次发现时可能短暂报告 `_NODE_NAME_UNKNOWN_`；适配器现在等待身份解析后再绑定。Ctrl-C 分别停止本次适配器、VINS 与传感器 launch。

动态传感器台架仅供 debug：用 prepare_motion_world.py --output 生成全新世界，再将绝对路径传给 sensors.launch.py 的 world 参数。在相同 GZ_PARTITION 中运行 run_sensor_motion.py --output 记录运动。此工具依赖 Gazebo Python transport/msg 模块；它按 config/components/simulation/sensor_motion.json 向独立传感器刚体施加物理力和力矩，不能用于无人机飞行。不要恢复 VelocityControl：该方式曾产生运动图像却缺失对应 IMU 平移加速度。真值只记录至本地 JSON。完成后用 evaluate_vins_motion.py 的 --motion、--odometry、--output 做离线单次刚体对齐评估；该程序拒绝时间戳不递增或没有有效重叠的数据。

已知限制：旧运动台架因 IMU 缺失平移加速度造成约0.90 m 的动态误差，已修复输入；新物理台架一次结果约0.0253 m。真实输入回放中适配器达到 TRACKING，并在录包停止、IMU 过期后锁存且停止输出。正式阈值、重复校准与各故障的重复注入尚未完成；当前 `initialized`／`solver_usable` 不能证明精度，VINS `failureDetection()` 仍无条件禁用，角速度使用未去 bias 的源 IMU，传播源速度 frame 虽由适配器转换但尚无独立 EKF 验证。不能凭这些开发运行认定可飞。
