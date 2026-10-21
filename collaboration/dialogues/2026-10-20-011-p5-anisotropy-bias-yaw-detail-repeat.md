# P5 零偏移 bias 与 PX4 yaw 对齐诊断 #217

- 日期与任务 ID：2026-10-20，继续项目 Goal；run-local `0008` 零偏移 bias 复测及 PX4 对齐 yaw 只读诊断 #217。
- 用户约束：当前仅推进单 D435i 仿真导航；`0008`只作 run-local 实验；保留现有健康门和 PX4 控制权；最终组合不得输入真值；每轮结果写入轻量证据并保持 P5 状态由证据决定。
- 已执行：在自维护 `uav_px4_bridge` 现有只读 detail JSON 中增加 `alignment_yaw_error_rad`，采集既有对齐检查计算值。该字段不参与健康阈值、fault 判定或控制。使用与 #216 相同且哈希匹配 #207 的零平移/零 yaw 目标配置运行 #217；没有启动 truth 输入。
- 已确认结果：目标派发后估计器 `accel_bias_norm` 首次超过0.15 m/s²门限时为0.187455 m/s²；首次 localization invalid 的 normalized cost为0.699565，动作因 `localization_accel_bias_norm_exceeded` 中止。最后一个中止前新鲜 ACTIVE 对齐样本的yaw误差为0.052709 rad、平移误差0.014649 m，随后没有 `px4_frame_alignment_drift` 事件。LANDING阶段的对齐值变旧，不能用来反推中止时的yaw误差。
- 只读历史遥测对比：#214/#215横移首次bias越限在派发后3.854677/4.040592秒，零偏移#217在1.762286秒；零偏移#216没有越限，后来以 `long_tracks_insufficient` 失效。三次越限时normalized_cost都低于1.0，但track/视觉数量不同。四个run目录没有ROS bag、MCAP、DB3或逐帧preintegration导出；现有PX4 ULog不能代替VINS实际IMU输入。
- PX4 ULog：duration 26.22仿真秒，dropout为0；有EV position/yaw/velocity融合标记，GNSS aiding flags为0；最终 landed/disarmed，触地后短暂记录 DESCEND/failsafe。
- 结论修正：#217的零偏移目标也触发accel-bias门，撤回“bias事件和横移相关”的小样本关联；不能归因横移或 `0008`。#216的yaw误差分支判断仍只是推断，#217没有复现对齐故障。P5仍未通过。
- 相关证据：[轻量报告](../../progress/evidence/p5-vins-anisotropy-filter-bias-yaw-detail-repeat-20261020-217.json)、[改动记录](../../progress/changes/2026-10-20-011-p5-anisotropy-bias-yaw-detail-repeat.md)。
- 下一步：在run-local harness旁增加只读 `/sensors/d435i/imu` 采集器，按仿真源戳与VINS遥测对齐；不接入真值，不改健康门、控制或canonical探针，不放宽质量、freshness或PX4门限。
- #218随后在零偏移LANDING期间捕获一组新鲜yaw误差0.196549 rad并记录frame-alignment保护；run-local IMU observer因SIGINT时rclpy context被默认handler关闭而未写入trace。详细结果见[对话摘要#012](2026-10-20-012-p5-anisotropy-yaw-alignment-repeat.md)和对应轻量报告。
