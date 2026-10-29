# N08 #241/#242 支架准入诊断记录

- #241 launch 参数类型传错，在扫描前安全退出；没有修改源码或运行控制。
- #242 修正 planner 配置后启动，初始 N05 在线／离线门一致拒绝。支架扫描在 11/15 阶段因 normalized cost 2.487235 中止。
- raw VINS cost-group 快照显示该触发帧 visual 占 88.89%；prior 数值结构检查通过但未能解释单帧视觉残差。
- 夹具确认移除、PX4 fresh readback DISARMED/landed、bridge DISABLED；容器 stop exit 0。
- 无 post-release N05、compute-only、goal 或 XY。未改变任何阈值。

验证／分析：比对 #225 launch manifest 与原始 run 数据；重算 `sqrt(2*final_cost/residual_components)` 并检查分组和；`project.sh stop` 与 fresh ROS 状态读回。机器报告及 SHA-256：[证据](../evidence/n08-preflight-cost-spike-20261024-241-242.md)。
