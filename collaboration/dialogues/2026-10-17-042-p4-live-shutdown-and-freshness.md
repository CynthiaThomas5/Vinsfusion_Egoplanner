# P4 当前源码活动目标、锁诊断与定位新鲜度复测

- 任务：继续推进 GOAL.md 的 P4，并验证导航共享状态锁日志修复在 canonical /clock VINS→地图→EGO 链路中的表现。
- 用户约束：只推进单 D435i 仿真；不把 debug_truth 证据算作最终视觉验收；PX4 控制只能由 uav_px4_bridge 发布；不要修改旧实验来源；保存运行、对话、进度与证据。
- 调查：#76/#80/#81/#82 在目标派发前分别因 telemetry_stale、propagated_stale、propagated 源时间年龄和 IMU 接收停顿失败。#81 观测到63 ms propagated 年龄触发原50 ms门槛，独立估算接收年龄仍低于200 ms；因此只将 propagated 的 PROVISIONAL 源年龄门槛调整至120 ms。#82随后在约362 ms墙钟间隙（约0.211 s仿真时间）触发原有 imu_stale，未继续放宽。
- 决策：9项健康测试与1 s propagated 断流合成检查通过；P2阈值仍为 PROVISIONAL。#83虽完成 action/轨迹 ABORT，但运行时 PYTHONPATH 覆盖了新构建并带回旧的锁内 accepted-goal logger，故排除其修复验收。#84 的诊断模块由当前源码重新生成，hash 与 #77 最终构建源码一致。
- 已确认：#84在新临时容器、ROS domain 213、唯一 Gazebo partition 与 canonical /clock 下，定位保持 TRACKING，地图1,414点；1 s前置门和0.5 s导航本地状态／里程计门通过；同 goal/epoch B-spline、READY 与 navigation_node_shutdown ABORT 对齐，traj_server 清除轨迹，两个进程退出码0。当前源码诊断 trace 无超过5 ms的锁等待／持锁事件；本次没有慢 warning。
- 限制：#84是短时 action-shutdown smoke，不包含跟踪到达、障碍净空、地图故障、PX4或10分钟负载；没触发慢 logger，因此 blocked-logger 覆盖来自 #77 合成回归。#81/#82的运行间隙仍待压力和重复验证。
- 证据：progress/evidence/p4-navigation-live-active-20261017-84.json、progress/evidence/p2-health-guard-review.json、progress/evidence/p4-navigation-shutdown.json。
