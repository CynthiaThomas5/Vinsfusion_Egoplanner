# GOAL B/C/D/F EGO 手动目标与首条 spline 诊断

- 任务：在已就绪的单 D435i 多障碍地图中发送一个 EGO 手动目标，确认规划器是否输出 B-spline，并对首条规划曲线做离线 SDF 距离比较。
- 约束：保持 run-local 五步膨胀和−0.05 m地图下界；`flight_type=1`；不启动轨迹服务器、控制器、PX4或setpoint发布者；真值只由诊断进程离线对齐，运行节点不订阅真值。
- 决定：健康定位和 occupied map 就绪后，EGO收到单个 epoch-frame PoseStamped并发布一条B-spline。离线对齐后这条曲线对名义模型球包络的表面余量为正；同一轮EGO随后重复报告终点在膨胀障碍，且在深度／里程计超时后进入 `EMERGENCY_STOP`。由于曲线没有执行且其后planner状态不稳定，只保留为规划接线和理想几何诊断，不算避障、轨迹跟踪或GOAL F验收。
- 待决：区分终点碰撞告警与无controller／无位移输入造成的状态变化；持续定位下的MapStatus和重规划时序；实际轨迹、最小机体距离、支架／线缆和制动余量。下一步做短开阔目标并完整采集B-spline序列。
