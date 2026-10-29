# N08 #303 负侧视后健康门拒绝

## 用户约束
- 继续完成 N08 Goal；保持原有定位、地图、速度、机体、时间与跟踪阈值。
- 普通单目标到达并停住即结束；返航是另外的命令。

## 决策与结果
- #303 在负 Y 侧视和 yaw 回中后添加 15 秒中立保持，假设等待可让 VINS 恢复。
- SITL 在该中立保持阶段以 normalized_cost=1.0007072056 超过原 1.0 门限，15/19阶段结束；未生成 post-release N05 map，无飞行。
- 独立PX4读回确认DISABLED、disarmed/landed、control0；fixture清除，项目容器Exit(0)。
- 下一步 #304 缩短负侧到位后的额外静止观察段18秒至8秒，其他动作和所有门限不变。

证据见 [#303报告](../../progress/evidence/n08-negative-side-recovery-hold-refusal-20261026-303.md)。
