# P5 完整 VIO direct-clock 与零偏移目标复核 #195–#198

对话摘要：[2026-10-20-001](../../collaboration/dialogues/2026-10-20-001-p5-direct-clock-no-motion-followup.md)

## 修改与运行

- #195 被排除：launch 后检查发现 `uav_px4_bridge`、localization、mapping、navigation 实际解析到旧 `STACK_INSTALL`。修正 run-local overlay 顺序，在 #196/#197/#198 启动前强制检查自维护包前缀。
- #196 使用正确 run-local build，被动运行完整 VINS/localization/mapping/EGO/navigation/PX4 图35秒：PX4 收到318条 VIO，bridge detail 的 `px4_time_domain_valid` 全程为 true，EV position/yaw fusion 可见、GNSS aid 为零；无目标、控制、debug_truth 输入，车辆 disarmed。该轮 EGO 输入 source-age 有长尾并出现 timeout 日志，因此只作为时钟域与被动融合证据。
- #197 通过 localization、mapping、EV fusion 与5秒 PX4 freshness 门并完成解锁、起飞；bridge 随后以 `px4_timestamp_unavailable` 转 LANDING，导航 goal 未发出，PX4 landed/disarmed。该次不计 no-motion 目标尝试。
- `uav_px4_bridge` 新增 `px4_timestamp_error` 只读 detail 字段，保留原 fail-closed 控制行为。Jazzy 57项 bridge/frames/debug-param 单测与 Python compile 通过。
- #198 的 run-local build 通过6/6包构建；新字段未观察到映射错误。运行通过 freshness gate、Offboard、解锁、起飞并发送零偏移 goal，约1.10秒后 normalized_cost 从0.6147跃至1.0175，现有质量门中止 action。目标失败后 PX4接受 LAND、落地并 disarmed；ULog 中 battery flags 为零，Offboard signal loss 出现在 AutoLand 后，触地后 local-position relaxed invalid 再进入 DESCEND/failsafe。

## 验证与限制

- 通过 `python3 tools/test_px4_bridge_time_mapping.py`（18项）、`test_px4_bridge_control.py`（11项）、`test_px4_bridge_vio_profile.py`（7项）、`test_px4_debug_params.py`（2项）、`test_px4_bridge_frames.py`（19项）、`py_compile` 与运行脚本 `bash -n`。
- #196 运行中的被动 map/EGO observer 报告 source-age 长尾；不能宣称完整 P4/P5 图已稳定。
- #197 的 `px4_timestamp_unavailable` 在 #198 未复现；#198 不是成功目标，且没有 online truth，不能据此验证真实位移或定位误差。
- #198 保持 VIO future tolerance 65 ms、normalized-cost 1.0 和其他健康门限不变。P5 仍进行中；下一步检查越线附近的视觉残差／特征时序，不放宽门槛。
