# P5 telemetry源龄诊断与时钟投影

- 用户要求继续完成本项目完整 `GOAL.md`，不缩小范围；当前阶段 P5/P4仍在推进，P6及A–H未完成。
- 安全边界：本轮只运行VIO→EKF2 DISABLED/disarmed SITL；没有调用 enable service、发布控制、解锁或飞行；不订阅真值。
- #106首次逐PX4 topic捕获85/586次telemetry stale；#107增加clock采样但VINS只输出4条里程计且无EKF融合，故不用于融合结论；#108使用 `/clock`→monotonic拟合投影后仍有70/577次stale。#108观察到478条ROS VIO、506条PX4 ULog外部视觉里程计，EV position/yaw融合40/38次，GNSS aiding flags全零。
- 常规的异步clock样本比较已改为检查时刻的拟合仿真时间，阈值保持不变；静态测试及Jazzy单包构建通过。投影后仍有telemetry age问题；PX4 v1.17源码中的estimator flags和land-detected是事件型状态，不适合直接按持续源龄判定存活。
- 当前结论：P5 readiness未通过，末端DISABLED preflight失败；控制保持关闭。下一步为事件状态与周期遥测分别定义/验证liveness门，并继续完成P4/P5及GOAL A–H，不把当前诊断当成项目完成。
- 轻量证据：[P5 telemetry源龄与clock投影复核](../../progress/evidence/p5-px4-source-age-projection-20261017-108.json)。
