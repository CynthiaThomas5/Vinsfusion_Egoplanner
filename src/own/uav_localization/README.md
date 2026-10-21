# uav_localization

状态：首版 ROS 包已在 Jazzy 构建，并通过一次真实 VINS 输入回放。

`localization_adapter` 绑定一个不可复用的 VINS session manifest，监控六路输入源时间年龄、接收年龄、VINS 遥测质量、时钟及 VINS ROS graph endpoint identity。接收年龄按观测到的 ROS 时钟速率折算到仿真时间；源时间年龄和停钟墙时间门槛独立生效。达到连续健康帧门槛后，转发 VINS 优化位姿与 IMU 传播位姿，并将线速度转到当前 IMU child frame。故障锁存为 LOST/LOCKED，不在同一 epoch 自动恢复。

目前只输出 IMU frame 里程计；真实飞机安装外参尚未确定，因此不输出 base_link、TF 或 PX4 控制消息。VINS gyro bias 未向量化提供，角速度使用对应源 IMU 读数；上游没有位姿协方差，状态消息明确标记 covariance_valid=false。两次独立回放双目断流均触发 `left_stale` 锁定，两次独立相机 IMU 断流均触发 `imu_stale` 锁定；恢复输入后各自的同一 epoch 均不恢复。健康门槛为 P2 调试护栏，不是冻结验收标准或定位精度证明。

优化里程计 `/localization/optimized_imu_odom` 使用 reliable QoS，满足 EGO 规划器订阅端的要求，并兼容建图适配器的 best-effort 订阅；高频 IMU 传播里程计 `/localization/imu_odom` 保留 sensor-data best-effort QoS。
