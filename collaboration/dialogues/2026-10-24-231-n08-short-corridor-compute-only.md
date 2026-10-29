# N08.2u #231 任务摘要

- #230 的 +π/2 支架观察运行已安全落地，但 EGO 在 B-spline 前因 `planner_full_curve_unknown` 拒绝。action 后同身份地图上推断起点 hold sphere 有 309 unknown。
- 一度筛选的 +Y 释放位移方案不可由 N05 支架实现：`preflight_scan.py` 只有 x/z/yaw/pitch 四轴。该方案已撤销，没有更改 spawn 或改写 N05 约束。
- #231 保持场景、支持扫描 profile、释放点、规划速度和门限，只将 compute-only 目标 offset 改为 `[+0.10,+0.25,0] m`。旧图上目标 hold 和 0.50 m 后向 corridor 查询 free；起点 hold 仍 unknown，fresh run 决定能否形成有效曲线证书。
- 仅运行 DISARMED 支架 scan + fresh N05 gates + bridge-isolated compute-only。停止包络未证明，不执行 XY。

## 实际结果与交接

- 新鲜 N05 admission 和 compute-only runner 在有限范围内通过，READY spline 捕获成功；cancel 后 bridge hold、落地解锁均确认。
- 同身份地图几何证书因起点 hold sphere 的 209 个 unknown 未通过；curve sweep、目标 body/terminal hold 和 freshness 通过。没有 XY 或制动数据。
- unknown cells 集中在起点相对 ENU Y=-0.93…-0.83 m；后续单变量候选切到 `n08_overhead_rear_one_side_view`。同时保留 per-axis velocity criterion mismatch（捕获 Y derivative bound 0.08157 m/s，大于配置 0.075 m/s）。
- 详细证据：[报告](../../progress/evidence/n08-short-corridor-compute-20261024-231.md) 和结构化结果。
- 下一项 N08.2v #232：相同目标与场景，只改变 N05 observation profile；fresh N05 + compute-only，不执行 XY。
