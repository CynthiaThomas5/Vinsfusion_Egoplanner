# P2 EGO 跨 epoch 地图 reset 验证

日期：2026-10-17

- 用户目标：继续完整推进 [GOAL.md](../../GOAL.md) 的 P0–P6 与 A–H，不缩小最终范围。
- 用户约束：保留已有 staged／unstaged 修改；旧 EGO 与 vendor 来源只读；只推进单 D435i 仿真导航；不发送 PX4 控制、不解锁或实机飞行。
- 本轮关注：检查 VINS localization epoch 切换时 mapping adapter 是否先清理旧会话与 EGO plan_env map，再放行新 epoch 输入。
- 验证：在固定 Jazzy 容器独立 ROS domain 188 启动真实 EGO `plan_env`、深度健康节点和 mapping adapter。合成输入使旧 epoch 产生4个占据点；切换 epoch 后观察到清图。reset 等待期没有传感器样本，adapter 的深度／位姿输出计数保持5／8不变；新 epoch 输入恢复后观察到7组新配对 stamp，所有后续相机 pose 均为 `odom_<new_epoch>`，地图重新产生4个占据点。adapter 与 EGO 日志各确认一次旧 epoch 和新 epoch reset acknowledgement。
- 决定：保留这项结果为单次合成接口集成证据，不据此宣称 GOAL E 故障验收通过。独立 `/clock` 回退 replay 两次、真实 VINS restart 重复测试、地图几何、规划和 PX4 尚未完成。
- 限制：probe 的直接 synthetic odometry publisher 使用 best-effort QoS，EGO 可靠规划里程计订阅报告 QoS 不兼容；本次仅评 adapter→plan_env 的 depth／camera-pose/reset 路径，不评估规划输入与规划行为。
- 证据：[p2-ego-map-epoch-switch.json](../../progress/evidence/p2-ego-map-epoch-switch.json)，原始 ROS 日志与 probe 数据位于 `artifacts/runs/p2-mapping-epoch-switch-20261017-01/`。首次 harness setup 失败也保留，原因是 ROS setup 前启用了 shell nounset，修正后 runtime probe exit 0。
- 对应改动记录：[progress/changes/2026-10-17-016-p2-ego-epoch-map-reset.md](../../progress/changes/2026-10-17-016-p2-ego-epoch-map-reset.md)。
