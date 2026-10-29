# #214 N08 compute-only 失败诊断收敛

## 任务上下文

继续 N08 Goal 完成模式。#213 只证实 hold baseline；EGO compute-only 因没有 READY 曲线未通过。用户不要求降低门限，N07 的已通过运行不复测。

## 决定与修改

- Runner 在 READY 等待期间同时监看 action 终态，记录 task-level reason；失败时先取消活动 action，再禁用 bridge，并保存最终落地状态。
- Evaluator 现在要求 runner 自身明确 `PASS`；action 原因随评估报告保留。
- #213 离线 raw sphere 查询在 -Y 0.4 m 找到已观测 free 球候选，因此新增仅 compute-only 的候选 profile。在线 fresh N05 与目标查询仍是每次运行的硬门槛。

## 验证与未决

全仓库工具测试 284 项、N08 evaluator 3 项、VINS odometry evaluator 7 项均通过。没有用新 profile 重飞。N08 仍缺成功的 compute-only 取消／保持、EGO 执行、实际低速制动、三次独立运行和安全预算回填。
