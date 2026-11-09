# uav_localization

状态：首版 ROS 包已在 Jazzy 构建，并通过一次真实 VINS 输入回放。

`localization_adapter` 绑定一个不可复用的 VINS session manifest，监控六路输入源时间年龄、单调接收年龄、VINS 遥测质量、时钟及 VINS ROS graph endpoint identity。仿真仍使用 `/clock`；硬件 rig 要求 `use_sim_time=False`，用系统 ROS 时间计算源龄、monotonic 计算接收龄，并可启用按静置实测周期与空窗冻结的 freshness gate。硬件只有在 VINS 初始化、状态有限、当前求解可用且六路 age 均在预算内时才转发优化位姿与 IMU 传播位姿。线速度从 VINS world 表达旋到当前 IMU child frame。故障锁存为 LOST/LOCKED，不在同一 epoch 自动恢复。

目前只输出 IMU frame 里程计；真实飞机安装外参尚未确定，因此不输出 base_link、TF 或 PX4 控制消息。VINS gyro bias 未向量化提供，角速度使用对应源 IMU 读数；上游没有位姿协方差，状态消息明确标记 covariance_valid=false。两次独立回放双目断流均触发 `left_stale` 锁定，两次独立相机 IMU 断流均触发 `imu_stale` 锁定；恢复输入后各自的同一 epoch 均不恢复。健康门槛为 P2 调试护栏，不是冻结验收标准或定位精度证明。

优化里程计 `/localization/optimized_imu_odom` 使用 reliable QoS，满足 EGO 规划器订阅端的要求，并兼容建图适配器的 best-effort 订阅；高频 IMU 传播里程计 `/localization/imu_odom` 保留 sensor-data best-effort QoS。
# HW05 hardware image-health input

For a real hardware session, the stereo health subscriptions use `raw=True` and read only the original Image CDR metadata and pixel-sequence length. VINS still receives the full native image. Frame, encoding, dimensions, step, payload length, original source stamps, receipt ages, endpoint identity and freshness budgets retain their checks. The pixel sequence is a memoryview, not converted into Python image values. Unsupported encapsulation or truncated metadata fails closed. The simulation subscriptions retain their existing typed Image path.

Hardware admission also requires the configured one-second continuously fresh startup window. Numerical source/receipt budgets remain enforced, and a stale newly paired solution cannot reopen initialization after tracking.

`python3 tools/test_image_metadata.py` uses the installed ROS serializer to check the metadata reader; run it in the sourced ROS environment. The existing localization health regression remains `python3 tools/test_localization_health.py`.

The hardware start helper compares the actually imported node/health/metadata modules with workspace source before starting VINS. A mismatch refuses startup. Successful incremental build output alone is insufficient when copied installation/cache timestamps are later than the Nano clock; preserve generated old outputs and rebuild the affected package from a fresh build directory, then verify loaded bytes. The HW05 deployment correction is recorded in its evidence report.


HW06 硬件计算扩展：已绑定VINS发布者身份由原20Hz状态定时器持续核对（启动阶段也核对），
避免每条高频传播里程计反复扫描DDS图；每条消息的帧、epoch、时间戳和健康门保留。
硬件回调独占收到的Odometry对象，直接完成坐标/速度转换后发布；已发布源时间戳保证不会
二次转换。仿真仍保留原逐消息图查询与深拷贝路径。定向回归见
tools/test_localization_publisher_cache.py。VINS与硬件adapter默认使用同一份UDP大接收缓冲配置；
实际长时满载时效仍待HW09，未放宽HW04测定的数值预算。
