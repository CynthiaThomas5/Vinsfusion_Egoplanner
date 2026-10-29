# #368 动态障碍复测结果

关联：[运行协议](../evidence/n10-live-obstacle-clock-history-replan-protocol-20261027-368.md)、[结果报告](../evidence/n10-live-obstacle-clock-history-result-20261027-368.md)、[对话摘要](../../collaboration/dialogues/2026-10-27-368-n10-clock-history-retest.md)。

- 128 样本 clock history 下未出现 `odometry_time_error`；原 #367 映射拒绝没有重现。
- 方箱在目标后 12.016 仿真秒获得 Gazebo ACK；D435i/EGO表面点和同一 goal/epoch 后续样条均被观察。
- 目标仍以 `goal_timeout` 失败。Bridge 因项目自加的 0.15 m 平移对齐差门限在观测到 0.181539 m 时进入 LANDING；随后在 109.364 仿真秒落地。最高 yaw 差 0.047647 rad。
- 箱体采样净空扣减最大相邻样本包络运动后为 0.920173 m；禁止接触0。独立读回确认 LANDED、disarmed、control disabled、末态探针零控制样本；观察器覆盖终态，SITL 容器安全停止。
- 动态目标未到达，位置/误差指标无成功样本；N10.3 仍进行中。

下一项：移除项目本地平移/yaw对齐数值拒绝门，保留计算值用于诊断；运行定向测试与17包构建，再以新runtime重跑同一场景。
