# N08.2ab #238 任务摘要

- #237 证明 HRT/ROS `/clock` 差保持在毫秒级；41.376 s PX4-local-position/adapter odometry gap 出现在 localization `normalized_cost_exceeded` 锁存后。
- 本轮只改变 #237 stage16 yaw-return 速度：时长 16→48 sim s，其余同一 22-stage profile、门限和场景固定。目的为检验慢速返程能否保住定位健康并取得释放后 N05 证据。
- 仅 DISARMED 支架；若 N05 online/offline 同 identity 不准入，不运行 compute-only；不发 goal/控制，不做 XY。
- 结果仍在 16/22 stage 因 `normalized_cost_exceeded` 锁存，cost=1.091818，三倍慢速未解决。HRT/ROS gap −8…+12 ms；后续 PX4/adapter pair gap 28.432 s。
- 新的未解观测差异：adapter 状态报 normalized cost 1.091818；归档原始 VINS telemetry 在同 source stamp 推导为 0.863386，失败前后 3 sim s 的采样峰值0.941433。可能是外部未捕获短时消息，不能据此认定误报。下一步应只读记录 adapter 内部 Health.metrics/telemetry stamp。
- N05 before gate 拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`，无 post-release gate/compute-only。夹具已移除、DISARMED/landed，容器停止。详见 [evidence](../../progress/evidence/n08-slow-yaw-return-20261024-238.md)。


## #239 回查说明

#238 中把 raw VINS telemetry 与 LocalizationStatus.source_stamp 对齐后比较 cost，这不是同一指标时间戳：LocalizationStatus.source_stamp 表示 adapter 最近发布的 propagated odometry；normalized_cost 来自最新 Health.metrics telemetry。#238 因而不能据此判断 adapter 与 raw estimator 指标不一致，也不能认定 false lockout。#239 直接记录 Health.metrics.stamp_ns 后，与 raw VINS telemetry 同戳匹配，final_cost、residual_components 和重算 normalized_cost 完全一致；#238 本身没有留存该内部快照。详见 [#239 报告](../../progress/evidence/n08-health-lockout-readback-20261024-239.md)。
