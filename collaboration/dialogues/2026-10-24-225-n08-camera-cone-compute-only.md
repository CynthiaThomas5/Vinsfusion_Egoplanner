# 对话摘要：N08 #225 fresh map 与隔离 compute-only

- N08 继续按完整验收推进；N07 #198/#200/#204 通过项保留，不复测。
- #222/#223 水平观察在固定 normalized-cost 门处失败，不再追加相同类 yaw 扫描。#224 的 `[+0.8,+0.3]m` 仅为旧图候选，需 fresh map 复核。
- #225 复用 #221 的 15 阶段观察路径和同一顶板＋box/column 场景。fresh post-release 与 mission-time current-area N05 online/offline gate 通过，identity 一致。
- 新图中旧候选 terminal-hold 有 2 个 unknown，按既定门限拒绝。选用 `[+0.5,+0.2]m` 仅用于隔离 compute-only：同图 body/endpoint hold/continuous line 查询通过，顶板 raw occupied；start terminal-hold 仍有 42 unknown。
- Compute-only runner 记录 READY、cancel、2 秒 hold 和 landed/disarmed；bridge 订阅隔离输入，没有水平命令执行。N08 专用 evaluator 通过。
- 外层 mission 首次因通用 odometry evaluator 读取缺失的 localization history 返回 1。修复 evaluator 链，将 N08 专项诊断置于通用诊断之前；对原始输入副本重放 odometry 成功，缺失 status history 明确记为 unavailable。运行容器按项目流程停止，exit 0。
- #225 不代表 N08 完成：仍缺实际低速运动／制动测量、三次独立冷启动重复和 N05/N06 安全预算回填。完整证据见 [`#225 报告`](../../progress/evidence/n08-camera-cone-compute-only-20261024-225.md)。
