# P3 debug_truth EGO→PX4 闭环

- 任务：继续完成 GOAL.md P3，在 debug_truth 组合内把在线深度地图、EGO 目标轨迹与 PX4 Offboard 串接。
- 约束：Gazebo 真值只在 debug_truth；相机／PX4 参数保持唯一来源；`uav_px4_bridge` 是唯一 PX4 控制发布者；不把本轮真值飞行算作最终视觉验收。
- 改动：新增 P3 组合 launch 与 live flight probe；规划参数从 `config/components/mapping/ego_planner.json` 读取，intrinsics 从 D435i SDF 推导；导航与建图输入 remap 到同一 debug_truth epoch。
- 决策：#33 有目标到达但闲置 preset 航点造成 planner 空转，修正为 MANUAL_TARGET；随后 #34 干净复跑。DepthHealthMonitor 增加 ROS context teardown 时 RCLError 的有条件关闭处理。
- 已确认：#34 在线地图峰值2,047占据点；同 epoch EGO action 成功，938条 READY轨迹与 goal ID 匹配；唯一 PX4 bridge 发布控制，PX4 ULog确认EV融合、起飞／目标到达／降落、解除武装且无failsafe。阶段表 P3 因此通过。
- 限制：该路线未专门插入障碍，未验收障碍净空；整个 P3 运行使用 Gazebo 真值，raw SITL GPS 传感器仍在。P4/P5/P6 与 A–H 尚未完成。
- 证据：`progress/evidence/p3-px4-ego-flight.json` 与 `progress/evidence/p3-stage-exit-audit.json`。
