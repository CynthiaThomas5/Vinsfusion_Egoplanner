# N08.2m #223：水平观察分段回中

## 假设、唯一变量与判据

- #222 的 `normalized_cost` 越线发生在 yaw −π/2→+π/2 的连续转动期间。轨迹中 cost 从 0.6266 升到 0.9949，随后 health 读回 1.0097；这支持长连续转动是候选原因，但尚不能证明因果。
- 本轮唯一变量是水平视角之间的 yaw 路径：左视角保持后先回 yaw=0 并停留，再转向右视角；场景、两侧视角、保持时间、N05/EGO 门限及 unknown 规则不变。
- 判据：支架 scan 完成、定位始终有效、fresh same-run N05 after/post-release online/offline gate 通过；起点／目标 body spheres、terminal-hold spheres、完整候选曲线和顶板 raw occupied 分类均需同图通过。未满足则不启动 compute-only；无停止边界时不执行 XY。

## 允许范围与产物

- 新增 profile `n08_terminal_horizontal_views_via_neutral`；保留 #222 profile 和所有既有参数，用于可复查重放。
- run：`artifacts/runs/n08-20261024-223-horizontal-views-via-neutral-01/`。
- 证据：`progress/evidence/n08-horizontal-views-via-neutral-20261024-223.{md,json}`。
- 来源：[N08 #222 报告](../evidence/n08-horizontal-views-20261024-222.md)；[#222 变更记录](2026-10-24-222-n08-horizontal-views.md)。

## 实际结果

- 扫描在第 16/23 阶段、刚开始从 neutral yaw 转向 +π/2 时因 `normalized_cost_exceeded` 中止，最终 cost 1.00292；回中停留最后有效 trace 已到 0.97904。原 threshold 1.0 未变。
- 左视角及回中成功，右视角未完成；fresh post-release N05 gate 和同图 raw 查询均未发生，compute-only／XY 未启动。
- 通过 fresh DISARMED／landed 读回、fixture detach／模型移除后停止容器。详见 [#223 报告](../evidence/n08-neutral-horizontal-views-20261024-223.md)。
- 中立回归不足以防止 cost 越线；暂停继续增加 yaw 扫动。下一子项 #224 改在 #221 合格 map 上离线筛选位于相机视场且满足已存在 production 几何查询的目标。
