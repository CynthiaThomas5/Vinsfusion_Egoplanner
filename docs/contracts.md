# 接口与坐标契约

以下是系统契约。首版定位状态与适配里程计、建图输入适配、plan_env reset 接口、地图状态查询、RGB-D 关键帧、`NavigateToPose` action 及 EGO 按 goal/epoch 取消路径已实现。已对一份同 epoch 的 live occupied cloud 完成归档与 PCD 回读；patch 0021 的只读体素快照服务已由 #297 纳入 canonical 依赖链并通过干净构建和接口 introspection。地图覆盖、free/unknown 几何质量、规划净空与 PX4 控制验收尚未完成。

PX4 v1.17.0 的 SITL DDS 冒烟确认：配置表中的话题名不一定等于 ROS 运行时话题名。PX4 DDS 客户端会对声明非零 `MESSAGE_VERSION` 的消息附加 `_vN`；本次观测到 `/fmu/out/vehicle_status_v1`（`px4_msgs/msg/VehicleStatus`），并在源定义中确认 `VehicleLocalPosition` 也带版本 1。`/fmu/in/vehicle_visual_odometry` 保持原名，PX4 端订阅数为 1。后续桥接必须按运行时名称解析状态订阅。证据及范围见 [P0 DDS 冒烟报告](../progress/evidence/p0-agent-px4-dds.json)；该运行没有发送车辆控制或证明 EKF2 融合。

| 数据 | 建议话题或 API | 生产者 → 消费者 |
| --- | --- | --- |
| 双目图像 | /sensors/d435i/infra1/image_rect、infra2/image_rect，mono8 | uav_sim → VINS |
| 相机内参 | 对应 CameraInfo | uav_sim → VINS 配置生成及地图适配 |
| 相机 IMU | /sensors/d435i/imu，sensor_msgs/Imu | uav_sim → VINS |
| 深度 | /sensors/d435i/depth，32FC1 米 | uav_sim → uav_mapping |
| 深度健康 | /mapping/depth_health，uav_interfaces/DepthHealth | uav_mapping → mapping_input_adapter |
| EGO 建图输入 | /drone_0_depth_image + /drone_0_camera_pose，同一深度源 stamp | uav_mapping → EGO plan_env::GridMap |
| 地图清理 | /mapping/reset_map，uav_interfaces/ResetMapping | uav_mapping → EGO plan_env::GridMap |
| 地图状态 | `/mapping/status`，`uav_interfaces/MapStatus`；`/mapping/get_map_status`，`uav_interfaces/GetMapStatus`（可带 `expected_epoch`） | mapping_input_adapter → 在线消费者 |
| 彩色 | /sensors/d435i/color/image_raw，rgb8 | uav_sim → 关键帧归档 |
| RGB-D 关键帧 | `/mapping/rgbd_keyframes`，`uav_interfaces/RGBDKeyframe`；保留两图与 CameraInfo 源头，分别附对应时间位姿、epoch/map_id 和标定哈希 | mapping_input_adapter → 只读后续消费者 |
| 优化位姿 | /localization/optimized_imu_odom，nav_msgs/Odometry | uav_localization → mapping_input_adapter |
| IMU 传播位姿 | /localization/imu_odom，nav_msgs/Odometry | uav_localization → 后续高频消费者 |
| 定位状态 | /localization/status，uav_interfaces/LocalizationStatus | uav_localization → 所有在线消费者 |
| 地图内容／快照 | canonical `uav_mapping` adapter 目前没有体素快照服务；canonical EGO `plan_env` 由 patch 0021 提供 `/mapping/get_occupancy_snapshot`（`uav_interfaces/srv/GetOccupancySnapshot`），返回 raw unknown/free/occupied 与独立 inflation mask | 服务已在 #297 通过依赖重建、干净构建和接口 introspection；覆盖、几何、时延、重影、unknown 安全、净空与规划仍需验收后才能宣称 GOAL C 通过 |
| 导航目标 | `/navigation/navigate_to_pose`，`uav_interfaces/NavigateToPose` action；目标 frame 必须是当前 `odom_<epoch>` | 用户／未来决策 → uav_navigation |
| EGO 目标 | `/navigation/ego_goal`，`NavigationCommand(goal_id, epoch, PoseStamped)` | uav_navigation → EGO FSM |
| 轨迹取消 | `/navigation/trajectory_cancel`，按 `goal_id + epoch` 匹配；EGO FSM 与 traj_server 均订阅 | uav_navigation → EGO 与 traj_server |
| 轨迹指令 | `uav_interfaces/PositionCommand`，携带位置／速度／加速度／yaw、轨迹 ID、goal_id 与 epoch | `ego_planner/traj_server` → `uav_px4_bridge` |
| 执行反馈 | action feedback/result：当前位置、位置／yaw 误差、状态、原因 | uav_navigation → 调用方 |
| 真值 | /evaluation/ground_truth/* | 仿真 → 只读评估工具 |

## 时间

保留源 header；所有仿真 ROS 节点使用同一 /clock。PX4 启动时间与仿真时间转换单独核验。深度使用采样时刻位姿，经有界插值／预测取得，禁止用最新位姿直接替代。`plan_env` 的 occupancy PointCloud2 header 记录发布时的 ROS clock；EGO 仿真 launch 显式启用 `use_sim_time`。当前动态 run 的点云 stamp 与仿真时钟一致，距最近优化位姿 4 ms，但没有测量地图融合延迟。阈值从基线测试冻结，不先写死为已验收参数。patch 0018 将 EGO manager/FSM/可视化及 traj_server 的轨迹时间戳统一到各自 ROS node clock，避免 `rclcpp::Clock()` 默认系统时钟与 Gazebo `/clock` 混用；`uav_navigation` 使用 rclpy ROS clock 的负向 jump callback 检测回退，不再为每条 `/clock` 消息额外调度用户回调。动态 run #06 的 B-spline 起始 stamp 与首条 READY 命令相差7 ms，末次观测仿真时钟为3.969 s，未观察到回退。此处只验证一次样条时间域对齐；同一短运行的深度／位姿配对间隔 P95为0.396 s、最大0.495 s，地图时序仍未达到稳定验收。

VINS 优化状态与 IMU 传播状态分别记录频率、延迟及健康；重发旧状态不算新观测。深度 16UC1 毫米若作为兼容输入，显式转米，不能把 NaN、Inf、零深度当自由空间。

## TF 与单位

```text
map → odom → base_link → d435i_link
                         ├─ d435i_imu_frame
                         ├─ infra1_optical_frame
                         ├─ infra2_optical_frame
                         ├─ depth_optical_frame
                         └─ color_optical_frame
```

局部 pose 使用 VINS 重力对齐局部世界（初始 yaw 自由），不代表固定 ENU 航向；optical 为右、下、前，PX4 边界用 NED／FRD。当前定位适配保留该局部位姿数值，仅将 epoch 隔离的 raw world frame 改名为 `odom_<epoch>`，不发布 `map→odom` 或 `odom→base_link` TF。VINS 原始世界方向和 IMU frame 后续接入其他坐标系时必须真实转换，不能靠改 frame_id。上游线速度为 world frame，适配器按姿态旋转到 IMU child frame；角速度取同一源时刻附近的 D435i IMU 样本。当前没有飞机安装外参，因此接口只表达 D435i IMU frame，不冒充 `base_link`。

相机几何以 simulation/models 为源；从模型生成 VINS 与地图配置并记录哈希，不能同时手改多份外参。仿真标定与真实相机 PROVISIONAL 标定分开存放。

## 会话和控制权

epoch 每次 VINS 初始化／重置重新生成；map_id 绑定 epoch；goal_id 标识任务，run_id 标识证据包。消息和 manifest 必须能关联四者。定位状态至少包括初始化、可用、退化、丢失、锁定及源观测时间。可用状态不等同于绝对精度认证。

当前首版 VINS 适配器只发布 IMU-frame Odometry：`/localization/optimized_imu_odom` 和 `/localization/imu_odom`，并以 `uav_interfaces/LocalizationStatus` 发布 `/localization/status`。优化里程计使用 reliable QoS，以兼容 EGO 的 reliable 订阅；IMU 传播里程计使用 sensor-data best-effort QoS，兼容高频消费者。状态消息保留可靠 transient-local 最新状态。由于上游没有有效协方差估计，状态消息 `covariance_valid=false`；消费者必须按状态门控，不能把零协方差解释为已知高置信度。飞机安装外参确定前不得把 IMU frame 替换为 `base_link`。P3 隔离的 `uav_sim.debug_truth_adapter` 另从 Gazebo `world`→`d435i_link` 生成 `/debug_truth/optimized_imu_odom`，为每次进程创建新 epoch，输出 `odom_<epoch>`→`d435i_imu_<epoch>`；复合模型中 D435i IMU 与 link 同位。此话题不复用 `/localization/*`，也不是最终视觉输入。

目标含 position、yaw、frame 和容差，支持取消、替换、超时与明确失败。任务模式只有 simple_waypoint 或 ego 一项活跃。`PositionCommand` 是规划轨迹采样，不是 PX4 控制设定点；只有 `uav_px4_bridge` 可发布 PX4 设定点与 OffboardControlMode，并检查位置、地图、轨迹与飞控状态的新鲜度。EKF 局部原点与规划坐标对齐单独记录。

`uav_navigation.node` 把 `TaskSupervisor` 接到动作 API。它只接受与新鲜 TRACKING 状态、当前 epoch 和最新里程计一致的目标；epoch 切换、无效／过期定位、ROS clock 回退、超时和显式取消会发出带 goal/epoch 的取消事件。EGO 在对应轨迹元数据中保留 goal/epoch，traj_server 只接受当前轨迹键的取消，并通过既有唯一 `/position_cmd` publisher 发 ABORT；过期取消不会停止后来目标。目标替换先取消旧任务再路由新目标。节点内部 shutdown 会 ABORT 活动目标并请求匹配清轨迹；executor 等待活动 action callback 完成，并保留一秒供 action result service 投递后才销毁 ROS node/context。合成测试覆盖该顺序；run #10 曾暴露客户端收不到终态结果的竞态，修复后 run #11 一次 live SIGINT 验证客户端收到 `navigation_node_shutdown` ABORT、traj_server 清除匹配轨迹且进程退出码为0。动态 run #06/#09 观察到目标规划和 caller-cancel；run #08 则在 caller-cancel 前因 `localization_propagated_stale` ABORT，0.4 s timeout 仍为 PROVISIONAL、根因未明。真实规划重复性、地图输入稳定性、轨迹跟随与 PX4 故障行为仍未验收。

## 地图和未来消费者

局部占据地图保留 unknown；无深度和视野外区域不能直接清成 free。`/mapping/depth_health` 的 `valid=true` 只表示最近收到结构匹配且时间戳递增的深度图像；状态门按稳态墙钟检测缺帧，格式异常关闭，深度源时间回退后锁定到进程重启。`mapping_input_adapter` 还要求定位状态有效，并对优化里程计作有界深度源时间插值；依赖 plan_env reset 服务清空 epoch 旧地图后才转发。EGO `plan_env` 零值像素安全修复使该像素不生成 free ray。合成 ROS smoke 验证了定位失效清图；动态 D435i/VINS run #08 观察到同 stamp 输入与变化中的占据点数，并保存点云作一次单墙探索几何对照。墙面最近残差中位数 3.63 cm、P95 7.31 cm，点云头时间戳使用仿真 clock；这些描述值没有冻结为验收阈值。动态 EGO 检查确认 reliable 优化里程计进入规划器。早期 sequential-start 失败与默认首个预设航点原点距初始 VIO 位姿小于 0.2 m 的保护阈值吻合；旧手动 waypoint 回调仍把 Z 固定为1 m并忽略 yaw。新的 3D+yaw `NavigateToPose` action 已连接到 EGO；动态 run #06 一次生成带请求 yaw 的 B-spline 并成功取消，但不包含轨迹跟踪或目标到达验证。补丁 0008 将最新手动目标排队，由 FSM timer 消费，避免 executor 内嵌套 spin；在重复目标运行中未复现 executor 崩溃。补丁 0007 使 close-to-goal 重试期间的 EGO 在 SIGINT 后退出；一次动态故障路径测试干净退出。重复停机与稳定规划尚未验收。两次动态受控深度 stale run 均观测到健康门 READY→STALE→READY、plan_env reset 新 map_id、占据点清零后同 epoch 重建；这两次注入时 EGO 已在 WAIT_TARGET；EGO patch 0009 使新鲜占据更新清除先前的 timeout 锁存，并开放可配置 map timeout。单目标动态 run #12 和 #15 均在 source-stamp 深度注入期间观察到 `EXEC_TRAJ -> EMERGENCY_STOP`，且早于健康门 stale/map reset；#15 的 B-spline active interval 覆盖安全状态、stale 转换与 map reset。故障前配对输入间隔 p95 均为0.132 s、最大0.231/0.264 s。run #20 的 EGO 内部诊断显示同步 callback 仍在前进，但所有 timeout 时的相机 pose 都低于旧有效 z 下界 -0.0099 m；占据更新停在27.985 s，直接确认地图边界拒绝更新。`ground_height` 经 patch 0011 暴露后由 config 设为 -0.15 m。run #23 在40.024 s no-fault窗口内保持 READY／TRACKING，窗口内无 EGO timeout。run #24 在相同无故障输入配置下记录415组配对输出，但窗口内有73条 EGO timeout；日志中的相机 pose 均在地图内，且独立 observer 在前三组告警附近看到配对源间隔最大0.231 s。源码显示 EGO 输入同步和50 ms occupancy timer 共用单线程 executor，timer 执行深度投影与 raycast；这是可能的调度积压路径，尚未由运行耗时数据证实。run #14 的更新间断及 run #21/#22 的早期诊断分别有内部回调和 observer 限制，详见[输入间隔诊断](../progress/evidence/p2-ego-input-interval-diagnostic.json)。0.4 s timeout 与 -0.15 m 下界仍为 PROVISIONAL；floor geometry、长时漂移和主动故障响应尚未验收。该 FSM 状态没有接入轨迹服务器、控制器或 PX4，不能证明车辆实际停住；恢复策略及有效阈值仍未验收。多场景重影／覆盖、地图快照回读和长时行为均未验证。地图快照需包含 frame、分辨率、范围、epoch、map_id、配置哈希和时间。累计几何地图可保存展示，不代表跨重启定位。

canonical patch 0021 从 `plan_env` 直接快照原始栅格，并以 exact epoch/map_id、融合深度时间与未完成更新状态作 freshness gate；它将 raw occupancy 分类与膨胀／虚拟 ceiling mask 分开。#292 的单次成功读回仅覆盖了配置地图体积的约0.205%，因此仅验证接口身份拒绝、序列化和归档一致性，不能作为覆盖或地图质量证据；patch 0021快照服务本身不改变unknown-space规划策略；patch 0020只在隔离run #289/#306试验，未进入canonical。#306在0.5 m run-local inflation下于相机运动后捕获4条spline，但首条与goal后地图并非同刻；最后快照采样中心线为known/free，仍有inflation-mask重叠和大量collision/rebound告警。unknown安全和规划验收继续pending。 #293 把捕获门槛推迟到第151组转发深度，记录15,537个已知体素（0.450%）；单次固定尺度轨迹对齐后，1,319个raw occupied体素中心距生成场景已知SDF表面中位数4.28 cm、P95 7.06 cm。该点数和残差只作单轮描述，不能证明覆盖完整、无重影、自由空间准确或可规划；同epoch多时刻快照仍待采集。

#294 在同一epoch/map_id/frame和固定0.1 m栅格下采集三份快照，known voxel数由13,688增至19,878和20,283；occupied集合Jaccard为0.702、0.885，occupied体素中心到同run SDF表面均小于0.10 m。固定尺度单一SE(3)对齐使用离线fixture truth，位置RMSE 8.31 mm。EGO无目标且记录36条 odom/depth lost告警；本轮仅为一场景一序列的增长／表面一致性探索，不能证明覆盖完整、地图无重影或规划可用。详细限制见[证据](../progress/evidence/p2-map-snapshot-temporal-growth-20261020-294.json)。

#295 复用同一候选安装与运动profile，在第二种箱体／圆柱布局抓取三份同epoch快照。known voxel增至21,983，raw occupied集合相邻Jaccard为0.601和0.683；所有occupied中心距场景SDF表面最大8.58 cm。墙面中位体素中心在相邻快照间移动约7 cm，接近一个栅格；可能源于可见采样集合变化，未证明ghosting。EGO没有输入timeout，但没有目标，不能说明规划器就绪。详细见[证据](../progress/evidence/p2-map-snapshot-temporal-growth-20261020-295.json)。

#296 在全新epoch复测第二布局；world SDF与#295完全相同。墙面区域体素中心的3.03→2.96→3.03 m模式重现，同位置跨run中位差0.6–3.5 mm；连续快照变化约67–68 mm。首帧72个occupied中心到已知SDF超过0.10 m，后两帧为2/5；首帧离群点均分配给大墙且位于现有中心墙面采样窗外（诊断窗而非正式ROI）。#298源时刻视锥分析显示两轮局部x中心都为3.05→2.95→3.05 m；#303将墙面前表面平移半个0.1 m栅格后，#302匹配时相复测的中心稳定为3.05 m，且无occupied中心超过0.10 m SDF距离。这支持grid-side quantization和全轨迹对齐共同影响离群尾部，但不证明根因、覆盖或不存在ghosting；见[#298](../progress/evidence/p2-visible-wall-roi-projection-20261020-298.json)与[#303](../progress/evidence/p2-map-grid-phase-shift-20261020-303.json)。

#304/#305在canonical #297安装下以直线被箱体阻断的目标执行planner-only测试。两轮各产生两条B-spline；离线单刚体对齐后，直线对箱体名义机体球余量约−0.435 m。首条规划曲线对箱体约+0.134 m、对墙约+0.074 m；第二条对墙约−0.024至−0.028 m，说明当前`obstacles_inflation=0.099 m`不能代表0.482 m名义机体球包络。#305目标后首个静止场景地图快照的中心线在两条轨迹上分别有422/1201与655/1201个样本落入unknown，未进入occupied或inflated mask；地图服务源戳晚于目标1.145 s、服务耗时1.043 s，快照不是精确同刻。两轮都未运行轨迹服务器或控制器；truth仅用于离线换算，且对齐窗口为静止1.9 s。结果定位出unknown处理和碰撞包络待修复，不构成地图可用于真实绕障的通过证据；见[#304](../progress/evidence/p2-ego-planner-detour-canonical-20261020-304.json)与[#305](../progress/evidence/p2-ego-planner-goal-map-alignment-20261020-305.json)。

`/mapping/status` 发布当前 `MapStatus`，`/mapping/get_map_status` 支持调用方传入 `expected_epoch`；epoch 不匹配时拒绝该请求。状态接口只统计 EGO 输出的 occupied PointCloud2 点数，不推断未观测空间或 free／unknown 数量。`/mapping/rgbd_keyframes` 以配置的最小间隔发布通过定位、深度和 map-reset 门控的样本，保留 RGB／深度及 CameraInfo 源 stamp，并用各自图像时刻插值相机位姿。`tools/export_occupancy_snapshot.py` 可将已记录的 `/grid_map/occupancy` 样本打包为 PCD 与元数据；它校验 frame/epoch、采样时间、map reset 日志及 float32 坐标回读，不是在线地图服务，也不导出 free／unknown。一次显式 `/clock` 运行中的 MapStatus／occupied cloud 同 stamp 快照与回读证据见 [GOAL C snapshot report](../progress/evidence/p2-mapstatus-occupancy-static-snapshot-20261020-273.json)；该静态单样本不代表地图覆盖、规划器健康或避障验收。接口在线可读不代表后续消费者使用安全已完成验收。对应 handoff live probe 证据见 [P6 接口探针](../progress/evidence/p6-handoff-interfaces.json)。

RGB-D 关键帧记录各源 stamp、K、外参、有效深度掩膜及对应位姿。后续语义消费者只读，不绕过导航及碰撞门控。
