# P5 #191 降落与 PX4 failsafe 时间线

日期：2026-10-19

## 本轮目标

继续检查 #191 的 PX4 LAND、Offboard signal loss、本地位置有效性、着陆和 failsafe 转换。只做 ULog 离线读取与固定 PX4 v1.17.0 源码对照；不改桥接状态机、PX4 参数、VINS 质量门或其他控制逻辑。

## 已确认

- 外部 MAV_CMD_NAV_LAND 在仿真38.244秒发送、38.252秒获接受，PX4于38.264秒进入 AUTO_LAND。
- `offboard_control_signal_lost` 于39.236秒置位，距 LAND 命令0.992秒；此时 PX4 已在 AUTO_LAND，ULog 的 Offboard mode requirement mask 只包含 OFFBOARD=14，不包含 AUTO_LAND=18，因此该标志不解释42.596秒的 failsafe/nav mode 变化。
- land detector 于42.220秒报告 landed/at-rest；`local_position_invalid` 于42.476秒，`local_position_invalid_relaxed` 于42.584秒置位；42.596秒 `VehicleStatus` 从 AUTO_LAND 切为 DESCEND 并标记 failsafe，44.228秒因 landing disarm。
- ULog 最后 PX4 external `vehicle_visual_odometry` 样本在38.116秒、最后一条 fused EV position 在38.172秒。它们在质量门关闭后停止，随后本地 XY 有效性下降；该顺序支持但单轮不能证明 EKF2 失效仅由 EV 停流造成。
- 固定 PX4 源码中 AUTO_LAND 要求 relaxed local position；该要求失效后模式不再 runnable，回退到 DESCEND 与观察到的状态一致。电池 warning/status 与 failsafe flags 均未报告电池问题；tone log 单独不作电池根因证据。
- 直接的 mode-fallback 路径现有运行与源码证据相互吻合；VINS `normalized_cost` 为什么越线、EKF2 位置失效是否有其他因素仍待查。P5 仍未通过，不改门限。

证据：`progress/evidence/p5-landing-failsafe-timeline-20261019-191.json`。运行时原始文件及离线解析报告保留在 `artifacts/runs/p5-px4-vio-ego-hover-20261019-191/`。
