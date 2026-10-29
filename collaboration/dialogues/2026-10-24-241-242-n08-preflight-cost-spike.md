# 2026-10-24 — N08 #241/#242 preflight cost spike

## 用户约束与任务
- 当前是 N08 Goal 完成模式，N07 #198/#200/#204 保留通过且不复测。
- 低速实际位移／制动必须等停止边界通过；当前允许 DISARMED N05 支架和 compute-only 诊断。不得降低健康或安全阈值。

## 决定与结果
- #241 启动配置误把 goal JSON 传给 planner 参数；无支架、无 goal，容器启动前置失败。
- #242 按 #225 manifest 使用正确 planner 配置。初始 N05 gate 拒绝；DISARMED 扫描 11/15 阶段触发 normalized_cost_exceeded=2.487235。raw VINS 的唯一触发帧以 visual cost 为主（88.89%），prior structure check 通过；具体视觉观测根因未知。
- fresh readback DISARMED、landed、at rest，bridge DISABLED；夹具已移除，容器 exit 0。
- 下一项只调整 N05 yaw/pitch 返回顺序，观察同一 gate 是否能通过；仍是无 XY 的 diagnostic。阈值和验收标准不变。

详细证据：[报告](../../progress/evidence/n08-preflight-cost-spike-20261024-241-242.md)，[变更记录](../../progress/changes/2026-10-24-241-242-n08-preflight-cost-spike.md)。
