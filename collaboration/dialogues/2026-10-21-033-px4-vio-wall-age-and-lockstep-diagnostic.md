# 任务对话摘要

- 日期与任务 ID：2026-10-21 / #033
- 用户目标与明确约束：继续完成 GOAL.md 的 P0–P6 单 D435i 仿真导航；保留已有工作区变更。最终组合禁止真值输入，PX4 控制设定点与 OffboardControlMode 只能由 uav_px4_bridge 发布。
- 已确认的决定：对 #384–#387 的 PX4 freshness 失败，仅在 run-local overlay 把 estimator_flags 和 land_detected 的 wall receipt limit 从 3.0 提到 4.0 秒；保留 source-age、future、PX4 preflight、odometry、alignment 和 localization 门。#388/#389 的探针在 enable_offboard 前退出；#390 使用标准零偏移 no-truth harness 检查预流和安全回收。
- Agent 建议及待确认项：不把 4.0 秒诊断值并入正式配置。#390 在 ARM/TAKEOFF 后触发 clock_mapping_rate_out_of_bounds，映射里程计龄超过既有0.3秒门并安全降落；需要在控制时序下配对记录 /clock 与里程计映射。
- 实施范围：新增三轮 run manifest、轻量证据与进度摘要；无自维护源码或 canonical 参数变更。
- 对应改动记录：progress/changes/2026-10-21-033-px4-vio-wall-age-and-lockstep-diagnostic.md
