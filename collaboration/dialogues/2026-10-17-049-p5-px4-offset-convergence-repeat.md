# P5 PX4 estimated_offset 重估独立复核

- 延续用户要求的完整项目目标；本轮只核查 P5 PX4/Agent 时间戳，不缩小 GOAL 范围。
- #110 使用独立 PX4 build 副本、ROS domain 226 和 Gazebo partition，被动运行45秒。没有 PX4 控制发布、enable、解锁或飞行；无 truth topic/订阅。
- estimated_offset 调整窗口14.595–19.779秒，与融合有效 #109 的15.121–20.638秒接近。attitude未来戳167/1820、local-position87/909，全部位于调整期间；收敛后两者P95年龄4.679/9.028ms。41次 detail源龄门违规均在该窗口，状态reason优先为 `localization_not_tracking`。
- #110 的 VINS 原始里程计有284条，左/右图像565/564条；定位适配器刚进入TRACKING便在0.747秒以 `left_stale` 锁定。PX4收到0条外部里程计、EV未融合，故从融合证据排除；只用于独立时间戳相关性。车辆保持disarmed且无控制样本。
- PX4固定源码中存在Timesync连续高偏差后重置滤波器的路径，但运行日志没有证明这次实际触发，根因仍待确认；PX4来源只读。证据：[progress/evidence/p5-px4-offset-convergence-repeat-20261017-110.json](../../progress/evidence/p5-px4-offset-convergence-repeat-20261017-110.json)。
- 下一步给probe增加 `observed_offset`/PX4 timesync状态，保留现有门限并重复有有效 VIO 的 run；P5、P4、P6和GOAL A–H均未完成。
