# EGO补丁

来源：https://github.com/ZJU-FAST-Lab/ego-planner-swarm ，commit `23a8d5a191711dd65633df689bd00f55d4dea8f9`，GPL-3.0-only；只物化5个规划包。

有效顺序：0001–0011 → 0017 → 0018 → 0019 → 0021 → 0035 → 0036 → 0037 → 0038 → 0039 → 0040 → 0041 → 0042 → 0043 → 0045 → 0046 → 0047 → 0048 → 0049 → 0050 → 0051 → 0052 → 0053 → 0054 → 0055 → 0056。具体应用根目录与strip见`dependencies/sources.json`；0036、0038、0039和0041按清单中的binary模式重放。

0035保留起始航向边界；0036对停止目标固定三次B样条末3控制点，约束终点、末速度和末加速度；非停止局部目标仍用原优化方式，碰撞／可行性检查保留。未纳入的unknown／扫掠／诊断候选不代表已解决，正式安全条款仍待验收。

补丁哈希、上游许可哈希、基准构建及当前验证范围分别记录在依赖清单和progress证据。

0037在同一基准提交、0036之后应用（src目录，-p1，GPL-3.0-only）：新增只读`/mapping/query_occupancy_sphere`；复用0021的epoch／map_id／融合新鲜度门，直接统计与闭球相交的raw体素，不用inflation mask代替unknown，也不修改地图／规划／求解器。单次半径≤2m、包围盒≤100000格是资源上限。查询及0021共享新鲜度检查；补丁和三个最终文件哈希锁在sources.json。#062记录17包构建、fresh fetch及不解锁验证；不构成轨迹或飞行安全通过。

0040在同一基准提交、0039之后应用（src目录，-p1，GPL-3.0-only）：增加只读`/mapping/depth_fusion_trace`，按当前epoch/map_id记录plan_env同步深度／位姿回调和射线投影、占据更新完成的仿真时间与steady-clock时间、源戳及计数；reset时清零计数并记录新身份。它只增加诊断发布，不改变输入、地图、规划或控制行为。补丁与`grid_map.cpp`／`grid_map.h`结果哈希锁在sources.json。17包构建、223项回归、三次idle epoch和当前版深度断流／reset验证见[#090 N03证据](../../progress/evidence/n03-depth-fusion-continuity-20261022-090.md)。

0041在同一基准提交、0040之后应用（src目录，-p1，binary重放保留advanced_param.launch.py的CRLF，GPL-3.0-only）：EGO最终曲线检查使用映射配置中与N05 body-reference clearance一致的raw occupancy sphere；每条终端／紧急停止曲线还检查N05配置的0.25 m hold neighborhood，开始与结束都复核身份和融合新鲜度。配置缺失或曲线／保持区查询异常时拒绝，记录查询数量与steady-clock检查耗时。它不发布PX4控制，也不授权飞行；SITL布局和地图证据见N06进度报告。

0042在同一基准提交、0041之后应用（src目录，-p1，GPL-3.0-only）：只读`/mapping/query_occupancy_sphere`读取最近一次完成的融合，即使新深度输入正在等待处理。它保留epoch／map_id／frame、source与occupancy更新时间、深度位姿健康及raw unknown／occupied／越界判定，与0041曲线证书的pending语义一致；不修改地图或规划，不发布控制。#107记录r32的ready状态下查询因pending门被拒；r33验证仍待运行。


0043在同一基准提交、0042之后应用（src目录，-p1，GPL-3.0-only）：当活动曲线因raw occupied／unknown／map边界被拒时，进入已有EGO emergency-stop状态，尝试当前位置的定点样条；该样条仍须通过相同full-body、freshness、identity和terminal-hold证书才会发布。保持失败后不自动重规划；地图过期、身份错误、resource错误和hold球不可证时继续发安全拒绝，不发布hold样条。只改变EGO规划输出，不执行轨迹或认证动力学停止。运行证据见N06 #116。

0044曾在#251后增加最多三次refine及最终动力学硬拒绝。按用户在#353的明确要求，该补丁已退出有效源链；历史补丁文件保留供追溯。当前回到上游一次可行性检查、必要时一次时间重分配的行为。该流程仍会在上游refine算法失败时报告规划失败。

0045在同一基准提交、0043之后应用（src目录，-p1，GPL-3.0-only）：当有效导航目标的位置在当前点0.05m内、但要求航向变化超过0.1rad时，EGO发布定点三次B样条，位置控制点不动，yaw控制点平滑转向；轨迹仍通过现有完整曲线与terminal-hold地图证书后才发布。16个控制点、2秒区间令180°转向的yaw导数凸包上界不超过0.43rad/s。它不增加PX4发布者；构建通过不代表yaw转向或N08返航飞行已通过，仍需新鲜SITL证据。

0046在同一上游基准、0045之后应用（src目录，-p1，GPL-3.0-only；补丁SHA-256=`b1f9aa0d69eb1dc9637bc7de51942666fde9c7aab054124344987d6502629d82`）：将明确的 caller cancel 与故障 abort 分流。caller cancel 保留 bridge 当前活动设定点，EGO 按当前 VIO 速度计算前向停车目标并用现有规划器生成替换轨迹；最终整条曲线和 terminal-hold 继续由同一 raw-map 身份／新鲜度证书检查。规划状态、速度支持范围或地图证书失败仍通过原 ABORT 安全退出。N08 候选停止距离由#260等历史末端制动数据加0.10m余量确定，仅供低速前向试验，不声称普适制动保证。构建及实际取消SITL仍是待验收项。

0047在同一上游基准、0046之后应用（src目录，-p1，GPL-3.0-only）：caller cancel的速度限界和停车距离公式不变，停止目标改为锚定取消时刻活动EGO参考样条的位置，再沿当前测得速度前进。#288显示取消时刻实际位置与EGO参考点相差约5.9cm，原0.246m目标相对EGO参考起点只剩约0.187m，被EGO固定0.2m近目标门拒绝；锚定参考点避免跟踪偏差压缩局部目标。活动参考无效仍fail-safe abort；完整曲线、raw-map身份／新鲜度、终端保持证书和速度支持门不变。#288仅提供失败根因证据；0047构建和新冷启动SITL仍需通过。

0048在同一上游基准、0047之后应用（src目录，-p1，GPL-3.0-only）：停用`/move_base_simple/goal`的旧直通订阅；该回调固定目标高度为1m，未携带goal／epoch／map身份，也绕过导航action的定位与raw-map准入。简单航点统一调用`/navigation/navigate_to_pose`，经同一准入后成为`NavigationCommand`，由EGO生成完整受地图证书约束的轨迹，PX4仍由唯一`uav_px4_bridge`控制。补丁不改EGO算法或PX4发布链；构建与topic graph检查待完成。

## 0049 — official EGO collision policy (#331)

基准仍为 sources.json 中的 ego-planner-swarm ROS2 commit，按 0048 后应用。用户 2026-10-26 明确要求采用 FAST Lab 官方起飞/未知空间规则。`grid_map/official_ego_collision_policy=true` 恢复上游 `getInflateOccupancy` 的 inflated-layer-only 判据；raw occupancy/snapshot 不清图、不改 unknown。官方模式停用项目附加 raw-known-free 全曲线/terminal hold 证书，保留原生 optimizer 和 collision callback。新增只读 point-query 端点仅把同一个上游谓词映射到 ROS2 action 层，并返回明确 `unobserved_not_occupied`，不把它标成 raw known-free。默认活动配置由 task_supervisor.json 唯一选择。官方参考 commit/hash 见 artifacts/runs/n09-official-policy-331/official-source-manifest.json。ROS2/action/epoch/健康修复为本项目适配，并非声称原官方 ROS1 部署逐字一致。


## 0050 — N10 最终样条可行性诊断（#340）

在同一上游基准、0049 之后应用（src 目录，-p1，GPL-3.0-only）：为上游原有单次 `checkFeasibility` 输出逐轴最大绝对速度／加速度、配置限值、容差和重分配 ratio。该输出仅供 N10 诊断；不增加复查、不改可行性判据或控制行为。补丁与最终文件 SHA-256 锁在 `dependencies/sources.json`；构建与 SITL 结果按 N10 记录。


## 0051 — N10 未触发加速度项的 ratio 哨兵修正（#341）

在同一上游基准、0050 之后应用（src 目录，-p1，GPL-3.0-only）：当没有任何 acceleration control-point derivative 越限时，`max_acc=-1` 是“无样本越限”哨兵，故令其 time-reallocation ratio 贡献为 0；有加速度违反时继续使用原 `sqrt(max_acc / limit_acc)` 项。该改动修正上游单次时间重分配的 ratio 计算，不增加最终动力学硬拒绝；patch/source 哈希见 `dependencies/sources.json`。

## 0052 — 用户授权移除额外取消停车速度准入（#348）

基准仍为 ego-planner-swarm `23a8d5a191711dd65633df689bd00f55d4dea8f9`，在 0051 后按 src 目录、`-p1` 应用，GPL-3.0-only。移除本项目 0046 引入的 STOP_HOLD 总速度 >0.100001 m/s 或垂向速度绝对值 >0.010001 m/s 拒绝条件；只在速度不是有限有效数值时拒绝计算停车轨迹。保留 EGO 配置的速度/加速度可行性、碰撞规划、epoch 和控制所有权。既有停车目标距离公式与 0.03 m/s 静止分支仍是停车策略，不构成速度上限；较高速度停车能力尚无本版本实测证据。补丁顺序、SHA-256 与最终源码哈希已登记于 sources.json。

## 0053 — 移除项目自加的全曲线准入与规划失败立即中止（N10.3/#366）

在固定上游提交及 0052 后应用，依据用户要求删除会额外按整条曲线查询 raw occupancy／地图就绪状态的 `certifyLocalCurve` 活动调用，并恢复上游在规划暂不可行时重试 `SEQUENTIAL_START`／`GEN_NEW_TRAJ`／`REPLAN_TRAJ` 的状态转移。官方 `getInflateOccupancy` 障碍碰撞、原生 `checkCollisionCallback`、深度超时与紧急停车仍保留；这不是关闭 EGO 自身的避障。#365 诊断显示规划器曾报告 refined trajectory hits obstacles，随后项目新增的立即终止把动作转成 `planner_full_curve_planning_failed`；该 patch 用于验证重试是否可恢复，不能先验声称障碍任务通过。


## 0054 — 移除项目占据查询的数值时效拒绝（N10）

在固定上游基准、0053之后应用（src目录，-p1，GPL-3.0-only）：删除项目增加的 occupancy update age 与 depth source age 阈值拒绝。响应仍返回 fusion/source 时间戳供观察；active-map epoch/map_id、查询几何、分类、首次融合及 EGO 原生 depth/odometry watchdog 保留。本补丁不改变官方 inflated-occupied 碰撞判据或控制路径。


## 0055 — 深度断流发布任务故障（N10.3）

在固定上游基准、0054之后应用（src目录，-p1，GPL-3.0-only）：活动导航目标期间，EGO原生深度超时不再只进入发布停止样条的`EMERGENCY_STOP`状态，而是调用已有`stopForSafety`，发布带活动goal与epoch的`MODE_ABORT`，锁存安全状态并清除目标。PX4 bridge的匹配故障落地路径和规划器进程退出监护在自维护源码中；构建与SITL最终落地／解锁证据仍待补齐。


## 0056 — 重规划间的航向跟随（N10.3/#410）

在固定上游基准、0055之后应用（src目录，-p1，GPL-3.0-only）：常规导航偏航使用 EGO 已配置的前视轨迹切向（`trajectory_time_forward_s=1.0`），避免短周期重规划反复从当前偏航重置后相机长期偏离路线；不用噪声敏感的瞬时速度角。保留既有偏航速率限制和平滑，目标偏航仍在轨迹末端三个yaw样条区间内执行；仿真源戳未前进时保持上次yaw并将yaw rate置零，避免零时间差求导产生非有限控制量。#409碰撞前机头与运动方向差约76.5°；#411验证瞬时速度角虽绕开原南侧路线，但机体偏航扫过约−78°至+117°，raw VINS位置误差P95升至0.478m、独立到达FAIL，故该版本不采用。前视切向版本的同场景回归待验证；该补丁不增加起飞、暂停或降落门。


## 0057 — N10.3/#414 regular trajectory-yaw rate diagnostic

在固定上游基准、0056之后应用（src目录，-p1，GPL-3.0-only）：仅将 `traj_server.cpp` 常规前视轨迹航向跟随的 `YAW_DOT_MAX_PER_SEC` 从 π 改为 0.10 rad/s，用于一次固定路线校准。任务末端已有的 task-yaw 样条覆盖不变。该值是诊断变量，不是冻结标准；不增加准入、暂停、取消或降落门。

## 0058 — N10.3/#414 read-only per-voxel fusion trace

在0057之后应用（src目录，-p1，GPL-3.0-only）：增加默认关闭、ROI范围受配置限制的 `/mapping/n10_voxel_update_trace`。每次映射 raycast 记录源图像/位姿戳、epoch/map、相机位姿、ROI中每个更新体素的 hit/miss 票数、选票、更新前后 log-odds 和分类。它不更改占据更新、膨胀、规划判据或控制；只有显式诊断配置启用时才创建 publisher。Launch 参数默认关闭。


## 0060 — 更新框外inflation来源与逐轴索引界（N10.3/#435）

固定上游ego-planner-swarm `23a8d5a191711dd65633df689bd00f55d4dea8f9`，在0059后按src目录、-p1应用，GPL-3.0-only。清空local_bound内inflated标记后，从扩展inf_step并裁至map bounds的raw occupied来源重建，避免框外occupied应覆盖框内却被遗漏；在toAddress前拒绝逐轴越界的inflation目标，避免扁平索引alias。未改raw分类、unknown规则、inflation值、轨迹或健康/起飞门。#431提取函数和#432独立完整plan_env真实类10案例通过；候选已应用，主工作区构建/正常飞行证据另行记录。当前不安排故障后校准。
