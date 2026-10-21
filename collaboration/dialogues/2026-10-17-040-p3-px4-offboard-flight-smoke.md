# P3 PX4 bridge Offboard 与 EKF2 融合 smoke

- 任务：继续推进 GOAL.md 的 P3，验证 PX4 ROS bridge、外部视觉里程计融合及受控 SITL 起降。
- 约束：仅单 D435i 仿真；debug_truth 证据与最终视觉 profile 隔离；PX4 控制设定点只有 `uav_px4_bridge` 发布；PX4 源码只读；不把单项 smoke 当作 P3 或 GOAL 完成。
- 决定：运行 #32 后保留 P3 `in_progress`。接下来将 EGO READY `PositionCommand`、在线地图避障、到达反馈接到同一控制出口。
- 已确认：#32 build 3 个 ROS 包通过；bridge 通过显式 enable/disable 服务进行 Offboard prestream、起飞、降落和解除武装。PX4 ULog 确认 EV aid 融合，GPS EKF 控制为0且 GNSS aiding flags 为0。桥接器独占4个 PX4 输入话题。
- 限制：#32 来源为 Gazebo debug_truth，SITL raw GPS 传感器存在；本次未输入 EGO 目标轨迹、未做障碍绕行或到达反馈，因此不能代替最终视觉闭环验收。完整报告见 `progress/evidence/p3-px4-bridge-offboard-flight.json`。
- 待办：在线深度图→EGO READY 轨迹→PX4 跟踪与目标反馈，随后执行失效降落和最终无真值组合验收。
