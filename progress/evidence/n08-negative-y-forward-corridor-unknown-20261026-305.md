# N08 负 Y 支架观察后前向准入仍因后向 unknown 拒绝（#305）

状态：支架路线达到 15/15，negative-Y 观察已到达；释放后 N05 与 mission 当前区准入通过。但 N08 前向轨迹／取消停止走廊在目标和解锁前因 unknown 拒绝，未飞行、未测取消制动。

## 支架扫描和 N05

- 新冷启动 profile `n08_overhead_free_sector_negative_y_side_view` 复用 #300 15阶段、402仿真秒路线，仅将正Y侧视窗口换成负Y水平侧视。15/15阶段完成，yaw−π/2 到达并回中。fixture 已 detached，Gazebo model absent，fresh LandDetector 为 landed。helper 在最后健康检查留下 `localization changed or became invalid during physical scan`，Exit 1；最后有效读数 cost=0.8111，故保留警告，不宣称helper无条件通过。
- before N05 在线／离线因地面候选不足拒绝；after、fixture removal后的post-release、mission current-area N05均在相同epoch/map以 `all_entry_phases_known_and_clear` 接受。ground plane z≈−0.35m、252个原始occupied plane voxel。mission只读preflight通过。

## mission拒绝与 unknown 定位

- motion-cancel runner在goal/enable前拒绝 `trial_corridor_or_home_pad_unknown_or_occupied`。N05 home-pad entry通过，但 N08 cancel-stop方向走廊不通过：起点保持球 unknown 105格，首个前向查询距离0m unknown 136格；普通0.6m前向 capsule首个query unknown 217格；terminal hold unknown 14格。首个查询中心约 `[-0.126, -0.068, 1.026] m`，cover radius约0.993m。
- 同身份raw map复算首查询 unknown cells：中心范围 x≈−1.15…0.05、y≈−0.55…0.95、z≈0.55…1.45m；136格中约85% x<−0.3m，最近格中心位于x≈−1.05m。缺口因此主要在起点后向/侧向体积，不是本次负Y扇区单独覆盖可解决的问题。没有改变未知拒绝或空间预算。
- `flight.json`明记`action_goal_sent=false`，PositionCommand与PX4轨迹设定点样本均0，无取消或制动数据。额外odometry evaluator因无合格完整运动记录触发严格源时间戳错误；braking evaluator随后因缺少odometry-evaluation失败，均为本次未飞行的次生评估问题。

## 安全末态

独立4秒PX4读回：bridge `DISABLED`、PX4 disarmed/landed、控制输出0。项目容器停止并以Exit(0)退出。

## 下一步

负Y侧视没有解除该run实际的后向hold unknown。下一子项#306围绕该run的同身份地图缺口，采用已配置的yaw−π rear-facing观察思路，在释放前增加后向视角并分段回中；保持N05/N08地图、定位、空间、速度和跟踪门限不变。post-release/current-area N05及N08前向／start／terminal hold全free之前不发目标或解锁。

机器可读报告和SHA见此JSON；完整运行在`artifacts/runs/n08-cancel-highspeed-prescan-20261026-305/`。
