# P5 VIO + localization RTF profile

- 用户目标仍是完成 `GOAL.md` 的全部 P0–P6 与 A–H；本轮继续做本地被动 SITL，不改 PX4 来源、桥接控制行为或健康门，不启动真机。
- #114以 ROS domain 230运行45秒：D435i、Gazebo Harmonic、PX4 v1.17.0 lockstep、XRCE Agent、VINS、定位适配器和 DISABLED bridge；不含 mapper/EGO，不发布控制，车辆 disarmed。
- #114测得 `/clock` 端到端 RTF 0.417311，observed-offset OLS斜率 −0.583264秒/墙秒，14.7942秒出现一次 estimated-offset 归零并随即重建。与无VINS/localization的#113（RTF约1、无reset）对照，继续支持全视觉负载下的时基漂移关联，未识别具体根因。
- 主机/容器16逻辑CPU，无cgroup CPU配额；26个Docker统计样本CPU中位498%、峰值734%。Gazebo `ruby`进程在 `docker top` 生命周期平均CPU样本中位154%、峰值240%，VINS中位54.25%；这些值覆盖启动和探测，不能证明主机整体饱和或确定单进程根因。`/clock` 收包间隔P95 51.515 ms，最长58.603 ms。
- 有效VIO送达PX4 280条，观察到EKF2 EV position/yaw融合；GNSS aiding全零，无ROS真值topic或bridge真值订阅。Readiness末端10秒覆盖率为0、bridge维持DISABLED；有43/343条telemetry-stale与284/343条preflight-failed状态。运行结果为诊断性，不能计P5通过。
- 下一步在固定门控与相机规格下加入mapper/EGO负载再测，并继续检查 `/clock` 长间隔的调度来源。详见改动记录和#114证据报告。
