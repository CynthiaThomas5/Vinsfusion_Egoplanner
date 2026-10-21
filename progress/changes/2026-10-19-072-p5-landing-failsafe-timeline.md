# P5 #191 LAND、Offboard 丢失与 failsafe 时间线

对话摘要：[`collaboration/dialogues/2026-10-19-072-p5-landing-failsafe-timeline.md`](../../collaboration/dialogues/2026-10-19-072-p5-landing-failsafe-timeline.md)

## 修改

- 在 #191 run 目录新增只读 ULog timeline extractor 与 JSON 输出，保存 MAV_CMD_NAV_LAND、mode state、failsafe flags、land detector、local XY validity、EV input/fusion 和 battery flags 的同一时基时间线。
- 新增固定 PX4 v1.17.0 源码核对报告；更新 CURRENT、P5 evidence index 与 milestone 证据列表。
- 未修改控制行为、PX4 参数、`COM_OF_LOSS_T`、VIO quality 门或定位 freshness 门。

## 结果

- LAND 命令38.244秒发出并于38.252秒获接受，AUTO_LAND 在38.264秒生效。Offboard signal lost 在39.236秒出现，约在 LAND 后1秒；PX4 已处于 AUTO_LAND，mode requirement mask 不会把 Offboard loss 应用到当前模式。
- 着陆于42.220秒确认；本地位置的 relaxed-valid flag 于42.584秒失效后，42.596秒 PX4 从 AUTO_LAND 切换到 DESCEND 并置 failsafe，最终44.228秒因 landing disarm。PX4 源码中 AUTO_LAND 要求 relaxed local position；此模式不可运行与运行中观测到的 DESCEND 回退一致。
- 外部 VIO 最后样本38.116秒，EKF2 最后融合38.172秒，先于本地位置无效约4.3秒。支持 quality lock 后 EV 流停止与后续 local-position invalid 的时间关系；单轮不能排除其他 estimator 因素。
- 电池 status warning 为0，battery_warning、low_remaining_time、unhealthy flags 均未置位；tone alarm 文本不作为电池触发证明。

## 验证与限制

- 运行 `python3 artifacts/runs/p5-px4-vio-ego-hover-20261019-191/analyze-landing-failsafe.py --ulog .../14_30_54.ulg --output .../landing-failsafe-timeline.json`，从保留 ULog 可重复生成相同事件序列。
- 这是 #191 单次离线分析，解释 immediate mode-fallback 路径，不解释 VINS normalized_cost 首次越线原因，也不构成 P5 成功或 failsafe-free landing 证据。
- 下一步保持1.0质量门，继续查视觉 cost/feature 时间线与 EKF 在停止 EV 后的有效性退出；如需决定源停流因果，再做有针对性的独立重复，不靠放宽参数使其通过。
