# #247 N08 负 Y 覆盖验证摘要

## 任务与约束

在 #246 已成功的慢回程 N05 profile 上，仅增加 x=0、z=1.0 m、yaw=−π/2 的观察、停留和回中，确认新鲜地图中起点 hold 的负 Y unknown 是否消除。速度门、unknown 规则、几何半径和 planner 不变；健康门拒绝时不继续 compute-only 或 XY。N07 已通过的 #198/#200/#204 不复测。

## 结果

负 Y 观察与回中完成。进入首次 z=1.0→0.5 m 下降后，VINS normalized cost 达 1.000494 并以 `normalized_cost_exceeded` 锁存；stale 观测为空，源龄约 64/68 ms，PX4 HRT／ROS 时间域仍有效。扫描未进入 post-release gate，故未获取同图负 Y unknown 计数，视角效果尚不能判断。无 compute-only、曲线证书、XY 或制动测量。fixture 已 detach 并从场景移除，fresh readback 确认 DISARMED/landed、bridge disabled、控制话题零样本；项目容器安全停止。

## 下一步

#248 固定负 Y 观察与其余阶段，只把首次 1.0→0.5 m 下降从 8 秒延长到 20 秒。此变量针对 #247 在下降开始约 4 秒后触发的代价越线；不放宽健康阈值。
