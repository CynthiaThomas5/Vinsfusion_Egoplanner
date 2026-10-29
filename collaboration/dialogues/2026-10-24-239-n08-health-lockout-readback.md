# N08.2ac #239 对话摘要

- 用户询问 N07 改为非连续累计通过是否合理、PX4 时间错位是否会阻塞后续。N07 #198/#200/#204 仍保留为 3/3，不复测；本轮针对 N08 的时间诊断。
- #237/#238 的 PX4 HRT 与 ROS /clock 差为毫秒级，PX4 time-domain 有效。不能用它解释 adapter 在 localization health lockout 后停止输出。
- 本轮只新增首次锁定时一次性 Health.metrics 快照；56 项定向单测和 17 包 ROS 构建通过。
- #239 run 的 Health.metrics stamp 506355999999 ns 与唯一同戳 raw VINS telemetry 匹配。final_cost=2366.574815、residual_components=4690、normalized cost=1.0045896413；确实越过原 1.0 门限。下一消息 132 ms 后 cost 回落，但 fail-closed latch 保持。
- cost 分项为 visual=1236.373、marginalization=1107.821、IMU=22.381。尚未证明更具体上游根因。
- 更正 #238：LocalizationStatus.source_stamp 是 propagated odometry stamp，不是 Health.metrics telemetry stamp；原 raw 同戳对比并非同一指标时间戳。#239 内部快照与 raw telemetry 同戳完全一致。修正已写回 #238 JSON、报告和对话。
- #239 HRT/clock gap −8…+16 ms，4056/4056 样本时间域有效，无 bridge timestamp error、无 /clock 回退。PX4 vehicle_imu duplicate timestamp 两条错误独立记录。
- N05 before gate 因 raw unknown 拒绝；scan 16/22 后中止。fixture removed，fresh landed/disarmed 读回，容器 exit 0；无 goal/control/XY。
- 证据：[N08 #239 报告](../../progress/evidence/n08-health-lockout-readback-20261024-239.md)。
