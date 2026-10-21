# P5 #192 去爬升目标消融与降落 fallback 重复验证

对话摘要：[2026-10-19-074](../../collaboration/dialogues/2026-10-19-074-p5-horizontal-motion-ablation.md)

## 修改

- 新增 run #192：从 #191 复用同一镜像、PX4/VINS 二进制、健康门与规划/桥接配置，仅把相对目标垂直偏移从0.15米设为0米；横向0.30米和yaw偏移保持不变。
- 新增 run-local 目标对照记录、固定 SE(3) 对齐、首次 quality crossing 分析及 PX4 ULog 时间线；P5 evidence index 与里程碑新增本轮证据。
- 未修改自维护/第三方源码、控制器、PX4 参数或任何门限。真值仅接独立只读 observer。

## 结果

- PX4 进入 Offboard 并接受目标；首次 `normalized_cost=1.09435` 越线发生在仿真36.664秒，约在目标派发1.482秒后。动作因 `localization_normalized_cost_exceeded` 中止；降落后 disarmed。
- 越线时请求目标不含爬升。Truth-only 离线中心差分速度约 `[0.008, 0.002, -0.022] m/s`，速度范数约0.023 m/s；命令已进入轨迹输出但真值运动很小。输入/双目/长轨迹计数74/73/48，高于此前十样本中位数65/64/38.5。
- 唯一 cost 分解中 visual 占86.23%，IMU占0.10%，marginalization占13.67%。与 #191 首次越线的 visual 89.03% 一致为视觉主导；这只确认 cost 组成，未定位具体视觉残差来源，也不证明动作派发导致越线。
- ULog 再次记录相同的落地后模式 fallback：外部 LAND 获接受、AUTO_LAND 生效；touchdown 后 local-position relaxed validity 失效，PX4 转入 DESCEND 并短暂置 failsafe，之后以 landing disarm。Offboard signal loss 出现在 AUTO_LAND 已生效后；battery flags未置位。

## 验证与限制

- `bash -n` run-local launcher；比较 #191/#192 目标配置确认只改垂直 offset；#192 PX4 二进制 SHA 与 #189/#191 相同。
- 运行 `tools/evaluate_vio_quality_alignment.py`、quality crossing extractor 和 ULog extractor；三份输出均可从归档输入重建并逐字节匹配。`project_status.py`、新证据哈希审计与 `git diff --check` 通过。
- 越线后的整段对齐误差包含 VIO/PX4 EV 流停止后的降落区间，不作为正常飞行精度验收。首次 crossing 的具体视觉来源仍未确认；P5 未通过，`normalized_cost` 门限维持1.0。
- 下一步用相同配置做 no-motion target/hold 对照，区分目标派发、轨迹变化和传感器/优化自然波动；不要先改安全门。
