# 2026-10-25 #265 N08 样条管道拒绝

## 范围

继续用户指定的 N08 Goal：完成有依据速度下的前向制动，并验证返航必须原地 yaw 约 180° 后由 EGO 按机头前向规划；禁止倒飞。

## 已确认

- #265 关闭了 N05 支架扫描期间额外 source timeline observer。15/15 阶段完成，post-release 和 mission current-area N05 均通过，同一 epoch/map_id。扫描器泛化定位警告仍未完全归因。
- 正确低速 planner profile、40 秒 preflight、起飞点 admission 和 24 个前向走廊 raw-map 查询均通过。
- 前向目标发出后 0.16 仿真秒，watchdog 因控制点凸包横／垂向偏离 5 cm 管道约 0.72 mm 而取消。高密度 de Boor 诊断样点显示实际曲线最大偏离 4.758 cm；这只是诊断近似，不能作为连续安全证明。
- PX4 最终 DISARMED/landed，bridge LANDED/control disabled，容器安全停止。未完成前向制动、转头或返航。

## 决定

#266 只修正 watchdog 的几何解释：检查真实 B-spline 全曲线是否在原 5 cm 管道内，使用导数控制多边形的速度上界推导采样间余量。门限不变。经相关回归与构建后，在新的 fresh N05/SITL run 重试。

## 证据

- [#265 证据报告](../../progress/evidence/n08-yaw-first-watchdog-tube-refusal-20261025-265.md)
- [#265 变更记录](../../progress/changes/2026-10-25-265-n08-reference-tube-refusal.md)
- 原始数据：`artifacts/runs/n08-20261025-265-yaw-first-return/`
