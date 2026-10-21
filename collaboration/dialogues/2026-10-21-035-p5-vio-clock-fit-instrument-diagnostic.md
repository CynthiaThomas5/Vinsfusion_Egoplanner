# 任务对话摘要

- 日期与任务 ID：2026-10-21 / #035
- 用户目标与明确约束：继续完成 GOAL.md 的 P0–P6 单 D435i 仿真导航；保护已有工作区修改；最终组合不订阅真值，PX4 控制设定点和 OffboardControlMode 由 `uav_px4_bridge` 独占发布。
- 已确认的决定：为解释 #390 的 `clock_mapping_rate_out_of_bounds`，仅在 run-local `time_mapping.py` 的异常文本附加斜率、样本数和时间跨度，不改判定条件、阈值或返回路径；canonical 配置仍保持 estimator_flags／land_detected 3.0 秒接收龄门。#391 使用此前隔离的 4.0 秒 overlay，仅作为诊断。
- 运行结论：#391 attempt-03 通过诊断5秒稳定门，完成近原点约0.87 m高度的 smoke navigation action，报告到达成功且最终 landed/disarmed。PX4 ULog 有 EV aiding fused 记录，`EKF2_GPS_CTRL=0`、GNSS aiding flags为零；GPS传感器消息仍存在。后续 `normalized_cost_exceeded` 使定位门失效并触发降落。instrumented mapper未复现 #390 的速率越界。
- 限制：4.0秒门高于canonical 3.0秒；目标没有横向绕障；没有冻结的GOAL D/E验收、多场景重复、完整净空或十分钟负载证据。因此不更新P5或最终Goal通过状态。
- 下一步：使用canonical 3.0秒门做控制关闭的同负载配对采样，记录 PX4 estimator_flags／land_detected 的源戳和bridge monotonic回执，以及同窗 `/clock` 回执与RTF；据此判断消息发布周期、仿真速度或DDS交付造成的接收龄超限。
- 对应改动记录：progress/changes/2026-10-21-035-p5-vio-clock-fit-instrument-diagnostic.md
