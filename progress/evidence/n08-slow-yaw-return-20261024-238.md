# N08.2ab #238：减速返程 yaw 未避免定位锁存

## 结果

把 stage16 yaw-return 从 16 延长到 48 仿真秒（角速度约降至三分之一）后，profile 仍在同一 stage、同一健康门失败。22 阶段中完成 16 阶段，下视姿态已到达；stage16 开始时最后 valid 的 normalized cost 为 0.858684，首次 invalid 报告为 1.091818，reason=`normalized_cost_exceeded`。减速假设不成立。

PX4 HRT 与 `/clock` 仍保持对齐：`px4_ros_clock_gap_sim_s` 在 −8 至 +12 ms，PX4 time-domain 样本全有效且无时间戳错误。定位锁存后 adapter optimized/propagated 输出停在约 507.280/507.348 s，raw VINS telemetry/optimized/propagated 继续至 535.724/535.724/535.760 s；PX4 local-position 与 adapter optimized source-pair gap 增至 28.432 s，bridge 进入 `localization_not_tracking`。因此源配对差仍是健康锁存的后果。

新增一个待查的证据差异：`LocalizationStatus` 报告 cost 1.091818，但 fixture 原始 VINS telemetry 在该 source stamp 的 cost 推导值为 0.863386，失败前后 3 仿真秒里记录到的最大值为 0.941433；全 run 收录的 3,081 条原始 telemetry 中没有一条推导值超过 1.0。可能有短时消息未被外部 recorder 捕获，也可能 adapter 当时使用的内部 telemetry 与归档记录存在关联差异。没有证据足以认定误报；下一步需直接记录 adapter `Health.metrics` 内部锁存快照。

运行前 N05 gate 以 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` 拒绝，online/offline 一致。健康中止导致没有 prescan-ready、after/post-release/current-area gate、compute-only、goal、控制或 XY。夹具已 detach、模型移除，PX4 `ARMING_STATE_DISARMED`、landed，bridge DISABLED；容器由 `project.sh stop` 停止，状态 `Exited (0)`。

## 验证与限制

- `python3 -m unittest tools.test_preflight_scan tools.test_n08_timeline_helpers tools.test_n08_curve_certificate tools.test_n08_compute_only`：43 项通过。
- runner shell syntax、5 个相关 Python 文件 AST、JSON、`project_status.py` 和 `git diff --check` 通过；结构检查有 80 个可选历史 artifact link 缺失提示。
- 完整 PX4/定位时间线与输入哈希见 [`n08-slow-yaw-return-20261024-238.json`](n08-slow-yaw-return-20261024-238.json) 及 `artifacts/runs/n08-20261024-238-slow-yaw-return-01/`。

N08 仍为 `in_progress`。这轮也证明单次执行可能被定位 fail-closed 状态阻挡，但没有复现 HRT/ROS `/clock` 不对齐；N07 累计通过规则不受影响。


## #239 回查说明

#238 中把 raw VINS telemetry 与 LocalizationStatus.source_stamp 对齐后比较 cost，这不是同一指标时间戳：LocalizationStatus.source_stamp 表示 adapter 最近发布的 propagated odometry；normalized_cost 来自最新 Health.metrics telemetry。#238 因而不能据此判断 adapter 与 raw estimator 指标不一致，也不能认定 false lockout。#239 直接记录 Health.metrics.stamp_ns 后，与 raw VINS telemetry 同戳匹配，final_cost、residual_components 和重算 normalized_cost 完全一致；#238 本身没有留存该内部快照。详见 [#239 报告](n08-health-lockout-readback-20261024-239.md)。
