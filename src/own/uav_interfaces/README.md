# uav_interfaces

状态：实现定位、建图查询、RGB-D 关键帧和首版导航任务接口；PX4 bridge 接口单独维护。

`LocalizationStatus.msg` 描述会话 epoch、定位状态、失效原因、VINS 源时间、机体坐标系、健康指标及适配器接收计数。`covariance_valid=false` 表示上游 VINS 未提供估计协方差，输出 Odometry 中的协方差不能用于精度判断。`DepthHealth.msg` 表示当前深度输入是否新鲜且消息结构有效；它不代表深度像素有效比例、地图完整性或定位有效。

`ResetMapping.srv` 由 mapping 输入适配器调用 EGO `plan_env`，请求按新 `epoch` 和 `map_id` 清空地图，服务不可用或确认失败时保持输入关闭。`NavigateToPose.action` 是带位置、yaw、容差、dwell 和 timeout 的单目标 API；action feedback 报告当前位姿与位置／yaw 误差，action client 可对 goal handle 调用 `cancel_goal_async()`。`NavigationCommand.msg` 与 `TrajectoryCancel.msg` 将当前 epoch 和 goal id 传给 EGO／轨迹服务器。`PositionCommand.msg` 是 EGO 采样轨迹，并携带 `goal_id` 与 `epoch` 供控制边界拒绝旧轨迹；它不是 PX4 控制消息。PX4 状态、外部里程计和 Offboard 发布已由 `uav_px4_bridge` 集中维护；控制保持 DISABLED，直到显式调用 enable 服务并通过状态门。合成 action 取消、旧 epoch 拒绝与 traj_server 匹配取消样例见 `tools/test_navigation_adapter.py` 和 `tools/test_trajectory_server.py`。

`GetMapStatus.srv` 可带 `expected_epoch` 查询当前 map_id、输入门状态、最近实际转发的深度 stamp、EGO occupied cloud 的点数／时间及配置哈希。占据云仍通过 EGO 的 `grid_map/occupancy` PointCloud2 只读订阅；plan_env 没有向此接口提供 free/unknown 数量，因此不伪造这两类计数。`GetOccupancySnapshot.srv` 则请求由 canonical EGO patch 0021 实现的只读局部栅格快照；调用者先确认 MapStatus，再把精确 epoch/map_id 传入。响应含 frame、源深度／融合／响应 stamp、origin/size/resolution、raw unknown/free/occupied 数组和独立 inflation mask。当前由 `tools/fetch_dependencies.py --source ego_planner` 重建的规范来源提供服务。构建及接口 introspection 见 `progress/evidence/p0-ego-snapshot-canonical-build-20261020-297.json`，在线快照证据见 #292–#296 报告。`RGBDKeyframe.msg` 保留原始 RGB、深度和 CameraInfo 消息头，并为两张图像分别插值对应时刻的相机位姿；同时携带 epoch、map_id 和 SDF 标定哈希。关键帧只在深度建图输入已通过定位、深度和 reset 门控后发布。

后续算法可在 ROS 2 Jazzy overlay 和 canonical stack 运行时执行 `python3 tools/probe_handoff_interfaces.py --output <report.json>`，作为最小调用示例。它读取定位与地图状态、验证旧 epoch 查询被拒绝、接收含 RGB-D 和双时刻位姿的关键帧，再以定位里程计中的观察位姿提交导航 action 并记录 feedback／terminal result。该程序不发布 PX4 控制消息。端到端接口运行见 `progress/evidence/p6-handoff-interfaces.json`；一次零距离 observed-pose handoff 成功不代表位移规划、避障或飞行验收。
