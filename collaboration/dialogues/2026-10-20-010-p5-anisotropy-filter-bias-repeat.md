# 任务对话摘要

- 日期与任务 ID：2026-10-20，继续项目 Goal；P5 anisotropy filter bias gate 复测 #214–#216。
- 用户目标与约束：继续完成单 D435i 仿真导航 GOAL；Ponytail 下选择小而可验证的步骤。只接受 P0–P6 范围；不使用运行时真值或完整世界地图，不放宽定位质量、freshness 或 PX4 安全门；诊断不作为 P5/GOAL 验收。
- 已确认决定：在 #211 的0.01 run-local filter 横移场景复测时，只让 run-local flight harness 保存已有 VINS `accel_bias_norm`/`gyro_bias_norm` telemetry。随后加一轮横移独立重复，以及一轮经实际目标配置哈希确认的零偏移控制；保留同一 VINS binary、过滤补丁、健康门、PX4 参数及控制路径，不改 canonical VINS 或自维护源码。
- 执行配置纠正：#215 目录最初按零偏移控制准备，但启动脚本仍从 #192 复制横移/+30°配置。检查生成的目标 JSON后发现标签不符，保留原 run 与日志并改按横移重复解释；run目录与source-patch-manifest留有纠正说明。真正的零偏移 #216 运行前后均校验目标 JSON SHA-256，平移和yaw偏移均为0。
- 已确认结果：#214/#215两轮横移目标均在动作派发后约4秒由估计器 accel-bias state门中止；#216零偏移 action达到 position/yaw hold且bias峰值低于0.15 m/s²。PX4 `px4_frame_alignment_drift`先于定位`long_tracks_insufficient`，初始位置对齐误差0.0101 m低于0.15 m门限，源码逻辑指向yaw误差分支，但该yaw误差未直接记录。#216报告未确认disarm，PX4 ULog则记录触地和最终disarm。该零偏移run不构成导航验收。
- 安全边界：三轮均无运行时 truth 输入；PX4 ULog均有EV融合、GNSS aiding零、无dropout，最终触地并disarm；触地后均有短暂 DESCEND/failsafe。详细数据与hash在 progress/evidence 对应报告中，不能以本摘要作为测试通过证据。
- 待继续：核对横移开始后的原始 IMU/preintegration 输入、优化 bias state 和视觉/轨迹状态；区分 VINS bias 门、track质量门及 PX4 frame alignment 的时间关系。独立启动run只能支持关联，仍需受控重复，保持现有安全门。
- 对应改动记录：`progress/changes/2026-10-20-010-p5-anisotropy-filter-bias-repeat.md`。
- 后续更正：零偏移复测#217也因估计器 accel-bias state 超过0.15 m/s²而中止；因此#214–#215的横移bias事件不能被解释为横移特有。#217的直接 yaw 诊断在中止前未见超限，且没有复现#216的frame-alignment故障；#216的yaw分支解释仍未验证。见[改动记录#011](../../progress/changes/2026-10-20-011-p5-anisotropy-bias-yaw-detail-repeat.md)。
