# N08 #241/#242：启动配置拦截与支架扫描 cost 锁存

## 结果

父目标 N08 仍为 `in_progress`。#241 在启动阶段失败；#242 正确启动，但未通过 N05 支架扫描，没有运行 compute-only mission。

- **#241**：误将导航目标配置传给 launch 的 `planner_config`，EGO 报 `EGO planner and mapping drone ids differ`。容器启动后在 VINS/EGO 栈就绪前退出，未生成 N05 fixture 日志或 fixture 结果，也没有 goal。复核 #225 的 launch manifest 后，确认 planner 配置为 `config/components/mapping/n08_low_speed_calibration.json`；导航目标配置只在 mission 阶段传入。错误已在 #242 命令中纠正。
- **#242**：同 `n08_overhead_calibration` 场景、`n08_overhead_free_sector_view` profile。初始 N05 online/offline 都拒绝 `ground_plane_insufficient_raw_occupied_voxels`。DISARMED 扫描在 15 段中的第 11 段后因 `normalized_cost_exceeded` 停止，健康读回 cost 2.487235（上限 1.0）。同 profile 在 #225 曾完成 15/15 并通过 post-release/current-area gates；#225 raw VINS 最大 normalized cost 为 0.860666，因此 #242 表明结果对冷启动／视觉优化帧敏感，不是固定阈值必然失败。

## 触发帧

raw VINS 的精确触发 telemetry 为 stamp `385672000000 ns`、final cost 12187.083、3940 residual components，按健康实现公式 `sqrt(2*final_cost/residual_components)` 得到 2.487235。相邻 raw telemetry 恢复到阈值下，但 fail-closed 健康锁存已阻止支架继续。一次性分组快照中 visual 为 10833.616（88.89%，3708 residuals），IMU 为 729.435（5.99%，150），marginalization 为 624.032（5.12%，82）。分组总和与 Ceres final cost 一致，prior evaluation、spectrum、rank 检查通过；这不能定位到单个视觉观测或证明具体根因。触发发生在 yaw/pitch 同时回 neutral 的动作段，作为下一轮单变量假设，不作为已证实原因。

#242 没有启用该轮 PX4 HRT/ROS 时钟 observer，所以不从本轮作时钟结论；#237–#240 的同类场景时间读数仍是毫秒级且有效。本轮夹具移除后新鲜 PX4 读回为 DISARMED、landed、at rest，bridge 为 DISABLED；容器 `tools/project.sh stop` 后 exit 0。

## 未完成项

没有 post-release/current-area N05 准入，没有 compute-only、轨迹、goal、XY 或制动数据。#241 和 #242 均不构成 N08 通过。详细原始文件与 SHA-256 见本报告的机器可读副本；#242 原始数据位于 `artifacts/runs/n08-20261024-242-overhead-free-sector-admission/`。
