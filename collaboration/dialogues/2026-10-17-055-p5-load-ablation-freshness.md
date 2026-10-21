# P5 RTF 负载消融与 freshness 失锁诊断

- 用户持续目标是完成 `GOAL.md` P0–P6 与 A–H；本轮只运行本地被动 SITL，不改变健康门限、PX4 源码或 offset 算法，不使用 truth 输入，不发送控制。
- #117 因 ROS domain 234 超过 Fast DDS 上限232而在PX4 DDS实体创建前退出，保留失败日志；修正后#118/#119采用VINS+定位+PX4共同只读探针。RTF分别0.4200/0.4189，offset斜率−0.5798/−0.5816，接近#114；但#118有0.671秒VINS telemetry/odometry收包间隙后锁定`telemetry_stale`，#119在全局clock/传感器receipt gap后锁定`propagated_stale`，两轮均无EV融合。
- #120只启动深度健康门与mapping adapter，没有EGO plan_env/reset service；adapter保持map-reset barrier，未产生地图。RTF0.3636，但不能据此判定活动建图成本。
- #121启动mapping、EGO plan_env/FSM与traj_server，不启动navigation supervisor。EGO清图可见并短暂进入WAIT_TARGET，但约0.721秒`/clock`与IMU收包空档后定位以`telemetry_stale`锁定，mapping gate关闭；没有地图点或PX4 VIO。RTF0.3713，offset斜率−0.6342。
- 多轮观测支持RTF与observed_offset漂移速率近似互补；加载组合有更低RTF，但输入间隙与探针/启动负载妨碍组件级归因。P5不通过。下一步先做时序对齐的profile/启动分段，避免放宽freshness门；再争取一段稳定的活动map+VIO运行后测规划和跟踪。
