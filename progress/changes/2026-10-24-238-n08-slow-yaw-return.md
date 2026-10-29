# N08.2ab #238：降低后向下视 profile 的返程 yaw 角速度

## 假设与唯一变量

#237 捕获到 LocalizationStatus 在 stage16 yaw return 初段从 normalized cost 0.95343 越线至 1.013814。PX4 HRT 与 `/clock` 保持对齐，后续 41.376 s source-pair gap 是 localization lockout 的结果。本轮假设：降低该 yaw-return 段的角速度可避免同一特征切换期间的 cost 越线。

唯一变量是新 DISARMED profile 的 stage16 持续时间：从 #237 的 16 sim s 增至 48 sim s（角速度缩为三分之一）。其余 21 stage、场景、spawn、健康门、N05／unknown／速度门限、桥接器与目标均不变。原 `n08_overhead_rear_down_view` profile 保留不变。

## 产物与执行范围

- 新 profile：`n08_overhead_rear_down_slow_yaw_return`，22 stages；新增 runner allowlist 和 profile regression test。
- Run ID：`n08-20261024-238-slow-yaw-return-01`。
- 仅运行 DISARMED whole-airframe support scan。若 profile 完成，记录 after/post-release N05 online/offline；仅所有适用 gate 同 identity 通过后才允许既有 compute-only。任何拒绝都不发 goal。无 XY。

## 判据

- 主要判据：22/22 stages 完成，LocalizationStatus 无效状态未被触发，normalized cost 不超过原 1.0 门限。
- N05 release/current-area 仍独立按原门限检查；门通过只构成 compute-only 前置，不等于 N08 通过。
- 失败保留 exact stage、source timeline 和 fixture safety cleanup；不调整门限。

对话摘要：[dialogue](../../collaboration/dialogues/2026-10-24-238-n08-slow-yaw-return.md)。

## 结果

- 验证通过：profile/observer/N08 相关 43 项单测；runner shell syntax、5 个 Python AST、JSON、结构检查和 diff 检查。
- Run `n08-20261024-238-slow-yaw-return-01` 在 16/22 stage 返程 yaw 仍触发 cost lockout（1.091818）。三倍慢速没有避免失效。原始 VINS 归档未记录到 cost>1 的 telemetry，和 adapter 状态读回不一致；本轮不能认定是误报，需直接采集 adapter 内部 Health.metrics 才能判别。
- HRT/`/clock` −8…+12 ms，time-domain 持续有效。健康锁存之后 PX4/adapter source-pair gap 扩至 28.432 s，bridge `localization_not_tracking`。
- N05 before gate raw unknown 拒绝，无 prescan-ready 或 post-release gate。安全清理 verified fixture removed、landed、DISARMED；无 goal、control、compute-only 或 XY；项目容器已 `Exited (0)`。
- 详情与原始哈希见 [evidence](../evidence/n08-slow-yaw-return-20261024-238.md)。父 N08 保持 `in_progress`。


## #239 回查说明

#238 中把 raw VINS telemetry 与 LocalizationStatus.source_stamp 对齐后比较 cost，这不是同一指标时间戳：LocalizationStatus.source_stamp 表示 adapter 最近发布的 propagated odometry；normalized_cost 来自最新 Health.metrics telemetry。#238 因而不能据此判断 adapter 与 raw estimator 指标不一致，也不能认定 false lockout。#239 直接记录 Health.metrics.stamp_ns 后，与 raw VINS telemetry 同戳匹配，final_cost、residual_components 和重算 normalized_cost 完全一致；#238 本身没有留存该内部快照。详见 [#239 报告](../evidence/n08-health-lockout-readback-20261024-239.md)。
