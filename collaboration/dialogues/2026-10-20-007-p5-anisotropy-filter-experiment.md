# 任务对话摘要

- 日期与任务 ID：2026-10-20，继续项目 Goal；P5 run #207。
- 用户目标与明确约束：继续推进文件夹中的 GOAL；遵守单 D435i 仿真范围、保留用户已有修改、最终视觉组合不接收真值、PX4 控制只由 `uav_px4_bridge` 发布。
- 已确认的决定：根据 #206 的图像统计，用仅供 run-local 的 opt-in VINS tracker 补丁测试 min/max Sobel structure-tensor eigenvalue ratio 0.01；normalized-cost 与 PX4 安全门不变。单次零偏移 action 成功不算 P5 验收。
- Agent 建议及待确认项：不把补丁加入 canonical VINS；之后用非零目标观察目标门与 freshness 行为。
- 实施范围：新增补丁 #0008、隔离构建与 SITL #207、离线残差/图像/ULog分析及进度证据；未改 PX4 安全参数、canonical VINS 源码或控制拓扑。
- 对应改动记录：progress/changes/2026-10-20-007-p5-anisotropy-filter-experiment.md
