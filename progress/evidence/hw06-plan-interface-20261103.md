# HW06 EGO 与任务接口：限定地面计算通过

状态：**passed，限定真实深度地图上的地面计算与接口验证**。用户授权HW06全部出口、Goal完成模式，仅受影响验证。本次没有PX4桥、控制、SITL或飞行。[变更](../changes/2026-11-03-003-hw06-plan.md)、[协作](../../collaboration/dialogues/2026-11-03-003-hw06-plan.md)。

最终通过的是**抬高绕过箱体的三维目标**。低位目标的拒绝与远期冲突均保留，没有把所有候选、纯低位右绕、真实执行到达或长期时效算作通过。

## 出口与实际证据

| 任务书出口 | 结果 |
| --- | --- |
| 同一真实rig、HW04里程计、HW05深度地图驱动既有EGO/traj_server/NavigateToPose | hardware_plan入口复用唯一地图owner，系统时间，真实K/CameraInfo/采样时刻位姿；无第二航点控制器 |
| 小范围候选、控制资格待HW08 | 原生单轴速度参数0.15m/s、加速度0.2m/s²、1.5m horizon、米制深度3Hz；测试侧向0.9/0.8m及前向1.25m、z=0.75m目标。原生IR/IMU未改频率；膨胀0.299m仍PROVISIONAL |
| /position_cmd输出、零PX4控制 | 实际graph唯一publisher为traj_server，consumer仅只读观察器；无/fmu控制publisher、bridge或debug_truth输入 |
| 可行目标、反馈、替换、取消、身份追踪 | run10/11真实曲线、goal_replaced、canceled/caller_cancel与匹配ABORT；UUID→NavigationCommand的epoch/map_id→Bspline/PositionCommand的epoch/goal_id一致。实际反馈归档，无action到达成功 |
| 实物阻挡直连的规划目标 | run15：测量箱体挡住直线，native生成更新轨迹，最终trajectory21完整曲线在前后两张同身份膨胀地图中密集采样均无占据 |
| VINS重启/epoch清旧任务、轨迹和地图，不自动续任务 | 同地图PID226360跨run15→16；旧目标hardware_localization_invalid/匹配ABORT，之后无旧READY；新epoch空图事件、新图回读、旧查询epoch_mismatch，未自动发新goal |
| 实时输出无持续积压 | 阻挡目标验证窗口约6s、pending最大2/配置上限16，新增有界丢弃1帧；没有持续增长。266条原始command回调、约100Hz，最大间隔22.8ms、最大接收源龄15.2ms。未扩大成长期资格 |

## 实物与曲线复算

用户尺量确认：镜头前端到障碍正面50cm，高42cm、宽22cm、厚10cm；左侧约20cm、右侧较大。相机/箱体保持静止。

- 1.15m低位终点本身被inflated地图拒绝。依据实际地图选择1.3m低位空闲终点后，生成曲线仍在末段与其它占据簇相交，未通过。
- 最终目标：camera前向1.25m、world/odom z=0.75m。实际目标约 `(-0.030, 1.263, 0.750)m`。从实测body位置到目标的直线，在独立50cm障碍平面处的depth optical坐标约 `(-0.011, -0.332, 0.500)m`，处于22cm宽、42cm高箱体范围；不是把目标改成无阻挡直线。
- 前后同身份快照中，直线4001点分别命中raw occupied281点、inflated occupied3166点。
- 最终trajectory21：28s的**计算参考时长**，5601点（≤5ms步长）在两张地图均无inflated占据，端点计算误差约3.5e-18m仅为数值一致性；不是实际到达精度。峰值速度模0.0905m/s，参考最高z约0.948m。
- 同一任务共发布5个版本：17/19的完整远期曲线各有冲突，约3ms/2ms内被替换；没有把它们记作完整曲线通过。按每版实际生效前段、额外50ms投递余量及末版完整曲线复算，均无inflated占据；实际记录的6个READY显示样本也无占据。原始266条回调计数/时序保留。
- 最终曲线raw分类全部为unknown；原生policy允许raw unknown，碰撞谓词使用inflated occupied。这里证明的是相对已观测占据的计算绕行，不是完整房间known-free、连续含桨净空或可直接试飞。
- run10侧向候选实测速度模0.183–0.194m/s；0.15是原生优化参数，**未资格化严格0.15硬上限**。本轮实际候选保持在0.2m/s以内。
- 快照源龄before/after约0.886/0.694s，新epoch16约0.434s，如实保留；没有宣称这些全部小于0.868s。EGO的receipt watchdog与只读query源龄诊断不同，原生query没有新增项目source-age否决。

[地图与曲线图](../../artifacts/runs/hw06-analysis-20261103/final-curves-and-map.png)。复算入口：
`python3 artifacts/runs/hw06-analysis-20261103/final_analysis.py`，结果 `final-analysis.json`。

关键身份：

- run15 epoch `7bfd45ac457e48278c420285ed8b0b72`，map `7bfd45ac457e48278c420285ed8b0b72-770ad2e5b95346d8aaf5b1ded56a1ab2`。
- 实物goal `ed94f21025c24f1f938a25544ab8f33f`。
- run16 epoch `67805d52bd0c4a82bec0b7e00ca1d310`，map `67805d52bd0c4a82bec0b7e00ca1d310-ce436bd7c2fb4809977b146c3ad21375`。

## 实际改动与源码一致性

- 固定上游EGO `23a8d5a191711dd65633df689bd00f55d4dea8f9`、GPL-3.0-only。旧Nano/本地vendor完整备份，9文件部署差异和diff保留；未改旧ROS_SEARCH/realsense来源。
- 修正0062上下文缺cstddef、0064已删除waypoint订阅的过时修改段；完整干净重放、许可/补丁/最终文件SHA核对通过。更正3个旧错误最终输出哈希，其余既有输出一致。
- 新增0066完整knot时间轴缩放，修正原生短曲线只延长中间区间、全时长不足；manager端点导数重拟合保持。没有恢复0044或新增在线完整曲线硬门。数值变化不继承历史SITL资格。
- hardware_plan复用hardware_mapping入口；新增hardware planner/supervisor候选配置。compute_only明确地面准入、不伪造airborne、不报告无运动到达；取消撤销参考，保留替换/超时/身份/失效路径，默认仿真策略不变。
- 硬件定位已绑定DDS身份由原20Hz状态定时器持续核对，含启动阶段；避免高频propagated逐条扫描图。硬件独占Odometry直接转换一次；仿真逐消息查询和拷贝保持。帧/epoch/时间戳与全部原健康预算未放宽。
- VINS和adapter使用同一4MiB UDP配置；米制深度3Hz。单独降频、UDP或5s启动延迟都未证明彻底消除源龄锁定，5s方案已撤销。
- fresh build-base/备份旧install解决较新mtime跳过安装；最终14个锁定vendor文件、7个实际import模块逐字节一致。只读记录器调用action/service，未发布传感器、定位、真值或控制。
- ActionServer在destroy_node时显式释放，修复Foxy晚期GC的InvalidHandle；执行器对照未证实根因，线程策略全部撤回，保持原默认执行器。mapping.json的source SHA描述HW05参数派生时的历史部署launch，原文件在prior-vendor，不冒充当前canonical源码。

## 验证命令与结果

- Nano独立build-base：`colcon build --executor sequential --packages-select traj_utils plan_env path_searching bspline_opt ego_planner --cmake-args -DBUILD_TESTING=OFF`，5包通过；0066后仅重建bspline_opt通过。导航/定位fresh build、实际import byte checks通过。
- `python3 tools/test_navigation_bridge_closeout.py`：8项；`python3 tools/test_localization_publisher_cache.py`：4项；health13项、task core10项、mapping input6项通过。
- Nano隔离ROS_DOMAIN_ID=88：`python3 tools/test_navigation_adapter.py --project-root "$PWD"`，默认执行器完整适配器回归通过；250Hz clock/active action最大pose接收龄0.061s。包含查询/取消/替换/3D yaw/身份/超时/clock regression/shutdown。测试夹具仅作Foxy API移植及拆分原期限下的busy/立即cancel两个独立时序断言，生产查询期限仍0.25s。
- `python3 tools/test_trajectory_server.py --traj-server .../traj_server`：实际ROS帧/yaw/错身份取消拒绝/停止保持交接/匹配ABORT通过。
- `tools/test_bspline_time_reallocation.cpp`：主机旧源码assert失败，新源码6/9/20控制点3/3通过；Nano链接真实installed bspline库同样3/3通过（时长、几何对应、导数、原生可行性）。
- 完整patch含0066 fresh fetch/hash通过；Python语法、shell语法、结构检查与diff检查通过。结构PASS不代表SITL；未重跑SITL/飞行。
- 最终复算同时校验物理直线、前后地图/归档hash、所有实际参考前段/末版全曲线、接口、epoch、publisher graph、清理和source指纹。

## 所有失败与支持边界

run01–16全部保留，未删除反例。01/02telemetry源龄锁定；5s等待无效；03缓存降低定位CPU但后续图像超时；04降频不充分；05/06仍锁定/服务查询失败；07/08接口和epoch有效但旧曲线超速；09查询超时/后续图像锁定；10新版侧向协议通过后图像锁定；11侧向/替换/取消通过而低位1.15m目标占据；12额外重复替换查询超时；13低位1.3m曲线远期碰撞；14重建身份但非最终几何通过；15/16为最终三维目标与生命周期证据。

持续源龄鲁棒性、完整满载资格仍留HW09；平均CPU收益不泛化。真实机体/含桨包络与时钟映射仍待HW08，rig保持PROVISIONAL、bridge控制不合格。不能把本次结果当成纯低位右绕、真实到达、完整环境安全或飞行许可。

## 终态、产物与下一项

所有所属sensor、VINS/localization、map/traj/nav、观察器和资源记录器已停止；最终进程/ROS节点为空，rmem恢复原212992。launch对mapping adapter从SIGINT升级SIGTERM，观察器也经PID/进程组身份核对后TERM退出；没有宣称所有Python节点均SIGINT优雅退出，没有控制链被强杀。

大数据 `artifacts/runs/hw06-plan-20261103-01..16`、sensors01..04、source-audit与analysis目录；核心hash索引 `artifacts/runs/hw06-analysis-20261103/artifact-sha256.json`。旧vendor/install/build备份保留在Nano source-audit目录，COLCON_IGNORE隔离。

停止原因：**HW06限定全部出口完成**。唯一下一项 **HW07.1：只读识别真实PX4固件/硬件与DDS消息版本，再实施该模块**；本轮未启动HW07。恢复须按已验证入口生成fresh session/epoch，按sensor→plan→观察器→localization启动，不重用旧epoch。
