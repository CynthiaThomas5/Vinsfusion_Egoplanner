# N08.265：full scan passed; first live spline hit conservative control-hull guard

对话摘要：[2026-10-25-265](../../collaboration/dialogues/2026-10-25-265-n08-reference-tube-refusal.md)

## 结果

- 关闭 N05 支架扫描期间的额外 source timeline observer 后，新 epoch 完成 15/15 支架阶段；扫描后、释放后以及 mission current-area N05 在线／离线准入通过，同一 epoch/map_id。
- 仍保留 fixture runner 的泛化定位状态警告。15911 个 trace 样本均 valid，但该统计不能排除短时遗漏；归因待查。
- 低速 planner 及 launch source hash 与 #260/#261 约束匹配。40 秒只读 preflight、起飞点 admission、24 个前向 corridor raw-map 查询通过。
- mission 起飞后，首条 EGO B-spline 因控制点凸包超出 lateral/vertical 0.05 m 管道 0.72 mm 被 fail-closed；执行器随即取消并降落。真实样条的 100001 点诊断最大偏离为 0.04758 m，但这是采样诊断，不是连续证明。
- 直接状态读回为 PX4 DISARMED/landed、bridge LANDED/control disabled。容器已停止。

## 下一子项

#266 保留 0.05 m 原限值，用导数控制点给出全曲线最大速度，并以采样半间距对应的 Lipschitz 余量验证整条连续曲线。增加对应回归覆盖后，用 fresh run 重新执行同一 N08 流程；不改 N05、定位或制动验收标准。完整数据和哈希见[#265报告](../evidence/n08-yaw-first-watchdog-tube-refusal-20261025-265.md)。

## 验证

- #265 mission：`bash tools/project.sh mission n08-20261025-265-yaw-first-return config/components/navigation/n08_forward_braking_trial_goal.json`，exit 1；明确 FAIL，最终已降落／disarmed。
- PX4／bridge ROS 最终状态读回：PX4 `arming_state=1`、`landed=true`；bridge `LANDED`, `control_enabled=false`、`armed=false`。
- 安全停止：`bash tools/project.sh stop n08-20261025-265-yaw-first-return`，exit 0。
