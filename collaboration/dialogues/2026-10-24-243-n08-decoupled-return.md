# 2026-10-24 — N08 #243 分离姿态回程

## 任务和约束
- Goal 完成模式继续 N08；N07 #198/#200/#204 保留且不复测。
- N05 support scan 必须 DISARMED；compute-only gate 通过前不发 goal，stop envelope 通过前不执行 XY。健康阈值不变。

## 本轮决定和结果
- #242 的 visual cost 尖峰出现在 yaw/pitch 同步回中。#243 只把该返回顺序拆开。
- 新 profile 进入最后垂直回程时发生 normalized_cost_exceeded=1.013032（门限1.0），完成14/16段。精确 health snapshot 触发于416.956s；marginalization与visual约各占一半，prior评估通过，单残差根因仍未知。
- N05 before仍因raw ground-plane voxel不足拒绝；未到release gate/compute-only。夹具移除并新鲜读回DISARMED、landed、at-rest；bridge DISABLED，容器exit0。
- 下一子项：只放慢最后垂直回程，检验该轻微cost crossing能否通过；其他路线、阈值及门控不变。

详细证据：[报告](../../progress/evidence/n08-decoupled-return-20261024-243.md)。
