# P5 #193 no-motion goal 对照被 PX4 telemetry freshness 打断

对话摘要：[2026-10-19-075](../../collaboration/dialogues/2026-10-19-075-p5-no-motion-control-invalid.md)

## 修改

- 新增 #193 零位移、零 yaw 的 run-local action/hold 对照，与 #191/#192 复用同一镜像、PX4/VINS 二进制、健康门和规划配置。
- 新增固定 SE(3) 对齐、质量越线与 ULog 时间线分析；将该轮登记为无效的 no-motion 对照，并加入 P5 evidence index 与 milestone。
- 未改控制行为、PX4 参数、健康门或第三方源码。

## 结果

- 零位移目标已派发，但桥在 flight probe elapsed 23.758 秒先以 `px4_telemetry_stale` 进入 LANDING；23.859 秒的下一份 freshness detail 中，attitude/local-position 源龄分别为 −104/−84 ms，相对65 ms future tolerance 超限。PX4 的 AUTO_LAND 状态在 elapsed 23.923 秒出现。
- `normalized_cost=1.12086` 首次越线在 elapsed 25.023 秒；当时已是 AUTO_LAND，truth-only 速度约0.766 m/s，主要为下降。动作最终因 normalized_cost 中止，但该越线样本不能作为静止/无运动对照。
- 该下降帧唯一分组代价 visual/marginalization/IMU约67.87/31.88/0.24%；它与 #191/#192 正常目标阶段的分解不宜直接比较。
- ULog 内事件顺序再次显示 touchdown 后 local-position relaxed invalid、AUTO_LAND 转 DESCEND/failsafe，随后落地 disarm。此处保留 PX4 ULog 时钟，未将它和 ROS `/clock` 直接混算。

## 验证与限制

- 运行 `tools/evaluate_vio_quality_alignment.py`、quality-crossing extractor、PX4 ULog extractor；输出重建后与归档 JSON 逐字节一致。
- `bash -n` 与 JSON 目标配置检查通过；`python3 tools/project_status.py`、证据 artifact hash audit 和 `git diff --check` 通过。
- 由于 telemetry stale 在质量越线前已启动 LANDING，本轮不能证明 no-motion target 是否触发 cost gate，也不能解释 Future-stamp guard 的最初来源。P5 未通过；下一步先核查 PX4 源戳映射并保持所有门限不变。
