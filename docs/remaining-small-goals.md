# GOAL v3 后续小目标：EGO 复用与剩余集成规划

2026-10-30收尾：当前用户约定的N01–N17仿真范围已完成，N15按用户排除而非通过；R01/R02及实机不纳入。本文件后文保留历史执行规划和当时缺口，最新状态以[CURRENT](../progress/CURRENT.md)和[最终验收](../progress/evidence/FINAL_ACCEPTANCE.md)为准。

> 当前策略更新（#331，用户授权）：执行 [FAST Lab 官方规则](official-ego-policy.md)，独立垂直起飞→悬停→EGO 目标；unknown 保留 raw 分类而不单独阻断规划。N05 五阶段 raw-known-free、支架扫描、N06 额外 raw-free 整曲线/hold 球证书属于旧诊断策略，不是当前起飞前置。下文旧证据／实验流程仅按记录的原策略解读；当前普通任务走官方规则 runner，N08 专项试验不自动套用到新策略。


制定日期：2026-10-22。总契约：[GOAL.md](../GOAL.md)；实际状态与唯一下一步：[CURRENT](../progress/CURRENT.md)；任务状态、依赖及证据登记：[milestones](../progress/milestones.json)。

实施规划修订：**2026-10-23 v3.1／#094**。本次结合上游 `ros2_version` 源码和 N01–N06 已有证据，替换后续实施动作中的重复建设与笼统调查，保留原 N01–N17 编号、依赖、全部出口和 GOAL v3 A–H 完成契约。只更新计划，不启动仿真、算法实验、飞行或实机操作；不增加任何运行通过状态。

这是从 #051–#077 研究和实现接续的执行分解。编写计划不代表完成其中任何运行任务。N01–N17 为当前仿真主线；R01–R02 为可选研究；H0–H5 仍为后续实机路线。任务编号与历史实验 #078、#079、#080 属于不同命名空间。

## 上游核对与系统分工

核对基准为 ZJU-FAST-Lab/ego-planner-swarm 的 `ros2_version` 提交 `23a8d5a191711dd65633df689bd00f55d4dea8f9`，与本项目 [sources.json](../dependencies/sources.json) 的 EGO 基准一致。当前已经复用了其五个规划包，不存在通过再克隆一次该分支就补齐视觉／PX4 链路的版本升级。

上游默认单机演示使用 `poscmd_2_odom` 把期望轨迹直接写成模拟里程计；开启 `use_dynamic` 后使用自带 SO(3) 控制器和四旋翼动力学。默认 `local_sensing` 构建关闭 CUDA，从完整点云按距离和方向筛选局部点云；另一 CUDA 分支才渲染深度。该分支没有 D435i 驱动、VINS 估计器或 PX4 Offboard 集成。其演示不提供本项目的视觉定位、真实形式深度输入、EKF2 融合和 PX4 执行资格。

可复查的固定源码：[仿真启动](https://github.com/ZJU-FAST-Lab/ego-planner-swarm/blob/23a8d5a191711dd65633df689bd00f55d4dea8f9/src/planner/plan_manage/launch/simulator.launch.py)、[模拟里程计](https://github.com/ZJU-FAST-Lab/ego-planner-swarm/blob/23a8d5a191711dd65633df689bd00f55d4dea8f9/src/uav_simulator/fake_drone/src/poscmd_2_odom.cpp)、[感知构建](https://github.com/ZJU-FAST-Lab/ego-planner-swarm/blob/23a8d5a191711dd65633df689bd00f55d4dea8f9/src/uav_simulator/local_sensing/CMakeLists.txt)、[建图](https://github.com/ZJU-FAST-Lab/ego-planner-swarm/blob/23a8d5a191711dd65633df689bd00f55d4dea8f9/src/planner/plan_env/src/grid_map.cpp)、[规划 FSM](https://github.com/ZJU-FAST-Lab/ego-planner-swarm/blob/23a8d5a191711dd65633df689bd00f55d4dea8f9/src/planner/plan_manage/src/ego_replan_fsm.cpp)、[优化器](https://github.com/ZJU-FAST-Lab/ego-planner-swarm/blob/23a8d5a191711dd65633df689bd00f55d4dea8f9/src/planner/bspline_opt/src/bspline_optimizer.cpp)、[轨迹采样](https://github.com/ZJU-FAST-Lab/ego-planner-swarm/blob/23a8d5a191711dd65633df689bd00f55d4dea8f9/src/planner/plan_manage/src/traj_server.cpp)。这是源码判断，不是本轮上游运行测试。

| 部分 | 已有实现与来源 | 后续处置 | 对应任务 |
| --- | --- | --- | --- |
| A*、B 样条表示／求导、轨迹多项式 | 上游 `path_searching`、`UniformBspline`、`polynomial_traj` 已导入 | 保留算法，不新增重写任务；输入／边界变化时验证相关行为 | N06、N08–N14 |
| 轨迹优化目标与 L-BFGS | 上游核心已复用；本地已有停止目标末端边界补丁 | 保留优化方法和已有有据补丁；只有定位到求解器缺陷才作最小修改，不因地图拒绝直接改代价权重 | N06、N08、N09 |
| 占据建图 | 唯一 `plan_env` 已接深度，已有无效深度／射线／身份与快照补丁 | 保留地图实现；只对可复现的 raw 分类、覆盖、融合／查询或 reset 缺口修复，不引入第二套地图 | N03、N04、N06、N09 |
| D435i 仿真模型与标定生成 | 本项目已有双目、相机 IMU、深度、SDF 和传感器桥 | 保留当前配置来源；需要新观测流程时只修改对应模型／运动／输入配置并作影响回归 | N01–N06；真实标定留 H0 |
| VINS 与定位适配 | 已有固定 VINS、`uav_localization`、健康与 epoch 处理 | 保留 raw VIO 生产链；不重写定位器，不为尚未解释的故障放宽健康门；真实设备接入留 H0–H1 | N01、N02、N07、N10、N15 |
| 深度时刻位姿与外参 | 已有 `uav_mapping` 插值、IMU 到 depth optical 组合和输入门 | 保留适配器；只修有证据的时间、frame、队列或 reset 问题。点云如被采用，必须明确已转换到地图坐标，不能仅 remap | N03、N04、N06 |
| EGO FSM 与轨迹采样 | 上游框架加本地 goal／epoch／cancel、仿真时钟、yaw 和停止边界 | 保留现有三维目标接入；核对活动曲线、终端／紧急 hold、时间与替换衔接，不恢复上游手动目标固定 1 m 的假设 | N06、N08、N09、N15 |
| 机体与空间准入 | 已有 N05 完整含桨包络、唯一误差配置和 N06 全曲线检查 | 必须收敛当前 unknown／入口缺口、阶段规则一致性和实测制动预算；拒绝正确与正向动作可行分别验收 | N05、N06、N08 |
| PX4 定位与控制桥 | 已有 `VehicleOdometry`、设定点、Offboard 状态机、坐标／时间适配和历史闭环 | 继续唯一 `uav_px4_bridge`；复用实现，检查当前版本实际 EV 融合、控制切换、反馈及故障。未有证据不新增另一控制器 | N07–N09、N15 |
| 导航任务 | 已有 action、三维位置／yaw、到达停留、取消／替换、超时与反馈 | 复用任务核心；补真实运动和拒绝矩阵，发现反馈与实际不一致再修接口 | N09、N11–N15 |
| 构建、启动、评估和归档工具 | 已有固定依赖、17 包构建、标准入口、独立评估、快照与 run manifest | 继续使用；仅补未覆盖字段／入口，后续验收统一版本和全部运行记录 | N10–N17 |
| 上游 fake drone、SO(3) 模拟器、随机点云感知 | 仅用于上游规划演示；不属于本项目生产组合 | 不迁入主链替代 Gazebo＋D435i＋VINS＋PX4，不把理想里程计或世界点云作为最终在线输入 | 所有最终仿真任务 |
| 多机通信／`drone_detect` | 上游多机工具；当前仅导入所需五个规划包 | 单机任务不启用，不将其改成 PX4 桥或通用视觉定位器 | 当前 N 主线不排期 |
| 真实设备、机载平台和实机 profile | 当前只有后续设计，没有本项目实机验收 | 仿真交付后按 H0–H5 接入／标定／验证；不照搬 SDF 数值或 Gazebo lockstep 时间配置 | H0–H5 |

“保留”表示不因本次上游审阅而新增代码修改任务，不表示上游实现自动满足本项目验收；已有补丁也不因为存在就被判为全部必要或已通过。补丁的输入、输出、基准、哈希、作用和对应缺口在 N06／N10 按证据审计。必要能力可以用既有第三方和本地代码完成，无需从零重写。

## 已完成交付与剩余出口的对照

以下为 #094 在 2026-10-23 对既有证据的承接摘要；正式状态仍只以 milestones 为准。`passed` 的支持范围不能扩展到飞行或新版本；`not_started` 不解释为功能没有实现。

| 原任务 | 已有交付／复用基础 | 尚需完成的工作 |
| --- | --- | --- |
| N01 | [#083](../progress/evidence/vio-full-state-baseline-20261022-083.md)：三 fresh epoch 的位置、姿态、速度、RPE、返回漂移与时序基线，限定低速未武装支架运动 | 原测量出口已交付，不重做；飞行运动、任务时距和新版本误差在 N07–N10／正式任务补证，roll／pitch 激励未覆盖仍保留 |
| N02 | [#089](../progress/evidence/n02-health-timing-20261022-089.md)：支持运动健康复核、当前双目 stale 锁存及明确约束 | 原限定出口已交付；#02 质量代价和 #04/#05 接收龄历史根因未决，N10 决定适用范围；N05/N06 新失败不能被该历史通过覆盖 |
| N03 | [#090](../progress/evidence/n03-depth-fusion-continuity-20261022-090.md)：三次各 150 秒 idle 融合、断流／reset／旧身份拒绝 | 原 idle 出口已交付；任务全程融合连续性在 N09／正式任务验收；N06 live query 的 freshness 问题另行定位 |
| N04 | [#091](../progress/evidence/n04-map-geometry-20261023.md)：两布局、多时刻 raw 几何／分类、遮挡和延迟可复算 | 原诊断测量出口已交付；false-free／false-occupied、表面漏分和近一体素时序位移未被消除，按 N06 缺口及 N10 标准处理 |
| N05 | [#092](../progress/evidence/n05-entry-20261023.md)、[#121](../progress/evidence/n06-ground-boundary-release-admission-20261023-121.md)：完整含桨几何与阶段规则；wall/corridor 全机支架释放后 online/offline fresh admission 均通过 | 限定的未武装入口与地图准入出口已通过；不构成起飞或飞行许可 |
| N06 | [#116](../progress/evidence/n06-emergency-hold-fallback-20261023-116.md)、[#118](../progress/evidence/n06-dynamic-obstacle-response-20261023-118.md)、[#121](../progress/evidence/n06-ground-boundary-release-admission-20261023-121.md)：两布局全机证书、fail-closed、重规划、动态障碍和合法入口都有证据 | planner integration scope 已通过；曲线未执行，动态制动归 N08，P6/S4 与正式飞行验收仍未完成 |
| N07 | 历史 [#054](../progress/evidence/gpu4090-deployment-20261022-054.md) 闭环、已有 EV 转换和 Offboard 桥 | 当前组合的真实 EV 融合及三次独立冷启动、各至少 30 仿真秒无目标悬停、落地上锁未验收 |
| N08 | 已有 hold、轨迹采样、控制切换与停止边界实现；历史对照可参考 | 当前合法区域内的低速制动量测、三方式对照、同版本至少三次目标重复、预算回填未完成 |
| N09 | 已有三维位置／yaw action、取消／替换／超时、目标球准入与历史 16 m 导航 | 当前组合至少三次有明显位移的目标、不同高度／yaw、简单航点与 EGO、不可达及任务全程地图新鲜度矩阵未完成 |
| N10 | [#461](../progress/evidence/n10-normal-navigation-calibration-closeout-20261028-461.md)、[#468](../progress/evidence/n10-final-candidate-regression-20261028-468.md)、[#470](../progress/evidence/n10-rebuild-regression-20261028-470.md)、[#471](../progress/evidence/n10-final-freeze-20261028-471.md)：当前版独立校准、revision 8 冻结复放、干净 ROS/PX4 重建、596 项回归與 3D/yaw PX4 代表任务均有证据 | 限定范围 N10 已 `passed`；故障后校准按 #434 排除，故障能力不计 N15；单次正常校准、5 个地图表面、x_positive 不支持及 VINS 队列容量未知均作为限制保留。N11–N16 的正式次数及协议不变，且尚未开始。冻结清单见 [#471 inventory](../artifacts/runs/n10-20261028-471-final-freeze/freeze-inventory.json) |
| N11 | 已有仿真／独立评估／报告工具 | 冻结后的空场三次正式冷启动未完成 |
| N12 | 已有 EGO 绕障算法和历史固定场景演示 | #519已审计累计三次独立正式合格（#498新规则重评/#501/#518）；失败与不足保留 |
| N13 | 已有固定房间多障碍集成和地图工具 | 冻结后的错位多障碍、在线更新／重规划三次正式验收未完成 |
| N14 | 已有 corridor 地图诊断和包络工具 | 合法宽度的窄道三次正式验收、高度／yaw 组合覆盖及不可达覆盖未完成 |
| N15 | 已有 stale／reset／cancel／错误身份组件及部分未武装故障记录 | 六类故障各至少两次的冻结组合检测、实际退出／运动、净空和最终 PX4 状态未完成 |
| N16 | 已有资源／队列／时序记录工具及短时任务 | 连续至少十仿真分钟的完整负载、实际任务和重规划未完成，不能拼接旧 run |
| N17 | 已有工程入口、文档、快照、关键帧和接口 | 最终 A–H／P／S／N 逐项回收、固定版本重建运行示例和准确交付未完成；历史 G 仍需回归 |


### 2026-10-28 N10 最终收尾（#471）

N10 已完成并冻结。#468 在 frozen revision 8 下复放 13 项当前范围必需指标，均为 PASS；故障终态保持 `INSUFFICIENT` 且非必需，这是用户 #434 排除 N10 故障后校准后的明确范围，不代表故障已资格化。#464 提供干净构建身份，#468 提供最终候选 596 项测试与集成回归，#470 在最终 runtime 指纹下完成代表性三维/yaw 任务、独立到达评估、零违规接触和落地上锁读回，#471 汇总冻结清单。当前正常定量校准只依据 #460 单次运行；不将异版本记录合并、不将校准计入冻结后的正式次数。N11–N14 仍各需 3 次独立冷启动，N15 六类故障各需至少 2 次，N16 仍需连续 600 仿真秒任务；全部维持未开始状态。详见 [N10 冻结报告](../progress/evidence/n10-final-freeze-20261028-471.md)。

## 本次具体替换了什么

原执行书已经要求复用实现，本次没有发现一个可以因上游存在而直接删除的 N 验收目标。调整的是实施方法和下一步定位：

| 原计划位置／容易误解的工作 | v3.1 的具体安排 | 保留的出口 |
| --- | --- | --- |
| N01–N05 尚以“当前缺少”的初始任务措辞描述 | 改为承接已交付的限定证据；只对后续修改影响项回归，未解项显式带入 N06／N10 | 不重置五项 passed，也不把诊断通过升级为动作通过 |
| N06 笼统“集成整曲线检查” | 接续已有 0039／0041 与 #093，先做 N06.3 起点／hold unknown 和 live readiness 的可区分诊断，再按证据进入 N06.4，最后恢复 N06.2 两布局正向集成 | 原整机连续扫掠、身份／新鲜度、hold、handoff、故障和开销全部保留 |
| 将规划失败等同于需要重写 A*／优化器／建图 | 先确认输入和合法完整机体区域，再排查已有求解器；仅对有定位证据的缺陷修改 | 不改变碰撞、unknown 或原误差预算以换取曲线 |
| N07–N09 容易被理解成新建定位桥、控制桥、导航 action | 改为复用现有实现，分层核验 EV 融合、切换／制动和动作反馈矩阵；发现缺口再最小修复 | 所有当前版本飞行、重复次数和独立指标保留 |
| N10 容易重复做最初第三方迁入／工程整理 | 改为当前最终候选的干净重放与构建、补丁必要性／作用审计、受影响回归和标准冻结 | 不能用旧 #052／#054 构建代替最终版本资格 |
| N11–N16 容易把现成上游演示或本地历史 run 抵扣正式次数 | 复用算法、场景生成和记录工具，按同一冻结组合执行正式矩阵 | 四场景各三次、六类故障各两次、连续十分钟均未削减 |
| N17 重新搭一套交付入口或替换为上游 README | 使用现有 project.sh／start.sh 和归档，补齐最终操作与限制；清理活跃文档过时状态 | A–H、独立接口、可重建示例和全部结果回收 |
| 为实机迁移提前改写整个 ROS／定位／控制架构 | 保留稳定模块与接口，H0–H5 再适配真实驱动、标定、机载平台、时钟和飞控 | 仿真不能替代实机验证，实机本轮不启动 |

不新增全局 SLAM、回环接管、自主探索、语义、多机、第二套控制器／地图或无证据的 DDS／平台迁移为前置。回环仍按 R01–R02 的既定条件决定；上游模拟器的理想状态不用于解除当前 no-go。

## 修改范围与回归责任

| 后续实际改变 | 必须核对的既有证据与回归 | 进入飞行前的要求 |
| --- | --- | --- |
| 深度投影、射线或 raw 分类 | N03 实际融合／reset、N04 几何／分类／遮挡、N05 入口及 N06 连续扫掠 | 两布局完成受影响回归；旧测量保留为原版本历史 |
| 观测流程、相机模型、时间或外参 | N01/N02 支持运动和健康、N03 源时刻配对、N04 地图、N05 释放转移 | 不用新动作直接继承旧支持范围；相应入口和健康通过 |
| 包络实现、接地阶段或查询谓词 | N05 全几何／阶段规则、N06 全曲线／hold／故障；不得无依据降低误差项 | 用完整几何和连续覆盖证明一致或更保守；必要标准调整先按 GOAL 给证据和建议，原出口仍未通过 |
| FSM、轨迹时间／边界或采样 | N06 活动／迟到／取消／handoff，N08 参考连续和实际停止，N09 三维目标／yaw | 不新增未经检查的运动段，不由 bridge 绕行或平滑掩盖 |
| PX4 桥、EV 或控制参数 | N07 融合／悬停、N08 制动／切换、N09 任务与 N15 故障 | 源时间、frame、唯一发布者及最终落地上锁实测 |
| 仅计划／报告 | 文档链接、JSON、状态依赖和 GOAL 条款一致性 | 不产生运行通过或起飞资格；本次属于此行 |

N01–N05 的原限定交付保持已完成；新修改的适用性回归由受影响的后续任务承接，不改写旧 run 或悄悄扩大历史通过范围。N10 把仍然有效的证据与需要重测的项逐一绑定最终版本。

## 执行规则

- 收到推进指令后，按 [AGENTS.md](../AGENTS.md) 自动选择／恢复任务，先报执行模式、ID、假设、输入版本、允许动作、出口和适用预算，再实施与验证。普通模式完成一项后交接；用户明确启动 Goal 完成模式时，连续推进指定 Goal 内必要子项，直至其全部出口通过，取消默认 30 分钟／两轮探索上限。纯答疑、仅计划和文档请求不启动实验；范围、真实阻塞、用户／系统预算和状态写回仍遵守 AGENTS。
- 所有任务复用已有实现。先检查当前工具／证据能覆盖什么，再补缺口；不重做已完成的 EuRoC 入门、传感器骨架或第三方迁移。
- 每个任务的正式状态只写在 milestones；本文件写要求，不维护第二套完成勾选。`not_started` 表示 v3 出口未取得证据，已有工作列在 `existing_evidence`，不表示模块未实现。
- 诊断指标先声明，正式验收标准在 N10 冻结。现有 PROVISIONAL 参数不能当作已验证安全预算。精度、输入健康、地图、轨迹检查、实际机体结果分别报告。
- 普通模式按 AGENTS 的默认预算和无新增信息条件收尾；Goal 模式将无新增信息作为复盘与调整假设的信号，有可行路径就继续，直到指定 Goal 完成。用户／系统明确预算、暂停或真实外部阻塞仍须遵守，未完成不得标通过。所需正式重复次数保持不变，不能换一个更容易的指标关闭任务。
- 代码／参数／构建变化记录影响范围，重跑相关回归；同一正式组合的成功不能从多个版本拼接。保存失败、中断、排除原因和原始哈希。
- N01–N06 优先使用已有未武装夹具、离线分析和合成组件。支架运动只验证感知／估计，不证明飞行动力学；真值仅由 debug_truth 只读记录，夹具不得依据真值在线修正 VINS。
- 任何解锁、位移、停止或降落动作，先满足其机体包络和观测条件。没有可验证的起飞／校准空间时继续修复入口，不通过关闭 unknown 门、任意自身豁免或真值辅助起飞。

## 第一组：明确定位与地图的可用范围

### N01 原始 VIO 位置、姿态、速度及漂移基线

**承接**：#057 的 16 m 飞行误差、#069 的重复返回漂移、已有源时间配对与评估工具。原始缺口是统一位置／完整姿态／速度／RPE／时序证据；#083 已完成限定支架运动出口。以下实施／出口保留为任务契约，不要求无变更重做；不能以该结果替代后续实际飞行范围的误差验证。

**实施**：固定当前源码、安装 binary、参数、模型、负载、相机 IMU 参考点与 frame；先回算现有可用记录，再只补缺失原始量。至少 3 个独立 fresh epoch 的未武装记录覆盖静止、缓慢平移、返回、yaw 和升降；运动及支持时长在运行前写入 protocol。raw VINS 是主结果，loop 观察结果另列。当前仿真中 Gazebo 真值点为 `d435i_link`，D435i IMU 在该 link 原点；VINS body frame 也由生成器定义为 IMU，因此 VIO 与真值直接比较，不能再把 `base_link` 到 IMU 的安装杆臂加到 `d435i_link` 真值上。该杆臂只用于机体点与 IMU 点速度换算及一致性核查。

**出口**：程序化输出位置 ATE、固定窗口平移／旋转 RPE、roll/pitch/yaw、速度向量误差、逐次返回漂移、源龄／接收龄／最大空窗、配对覆盖率及拒绝数；统一源时间、单位和参考点。速度参考来自独立真值速度，或明确误差／时间窗的真值位置差分，不能对 VINS 位置求差后自证；以 IMU 点测量时，须报告零点重合依据，并用 `v_imu = v_base + ω×r` 核对基座／传感器点换算，避免杆臂重复应用。一次初始刚体对齐、尺度 1，不重新对齐返回段。给出数据支持的任务时间／距离范围及尚未覆盖部分。测出误差是本任务结果，不等于定位已达到最终门限。

**交付**：轻量报告＋逐帧结果＋协议／版本哈希；真实缺失的采集或评估代码及相应验证。禁止仅再跑一次旧位置图后宣称补齐速度精度。

**默认按子项推进**：N01.1 核对现有数据／证据，交付“已覆盖／缺失字段／最小补充动作”清单，仅只读分析和写报告；N01.2 按清单补齐必要记录／评估工具并验证；N01.3 按固定协议补采缺失数据、完成至少 3 fresh epoch 的整体评估。只完成 N01.1 不能将 N01 标为 passed；N01.2／N01.3 超出单轮预算时继续细分并在 CURRENT 接续。

### N02 定位健康触发与时序失效的受控收敛

**依赖**：N01。承接 #059／#060 的越线、#067 的分子／分母敏感性、#068 的先验观测，保留原失败。

**接续（#094）**：#089 已完成限定出口；复用健康实现和已有输入退化验证。历史根因未决项进入 N10，新观测动作引起的健康失败按其真实条件记录，不为继续 N06 放宽门限。

**实施**：先确定当前版本能否复现既有触发；质量残差和输入 stale 分开处理。按相同运动／负载做单变量比较，优先复用已有 telemetry。将门触发与独立误差、图像／IMU、先验与窗口事件对齐；有根因证据后才做最小修复。

**出口**：每类已复现问题有机制、修复或明确运行约束及重复回归；当前支持运动至少 3 个 fresh epoch 不出现未解释的正常输入误锁，并证明真实退化仍可检测。旧故障未复现时报告适用条件和未解根因，不能声称已证明误报或完成根因修复；该不确定性进入 N10 的适用范围决策。若当前支持范围仍无法稳定运行，本任务不能关闭。

**交付**：受控对照、保留失败、最小补丁／配置理由、健康检测回归。禁止仅抬高 normalized_cost 门、延长等待或关闭锁存获得成功。

### N03 深度实际融合的新鲜度与身份连续性

**依赖**：N01；可与 N02 的不执行轨迹分析交错。承接已有深度源时间插值、epoch／map_id reset、DDS 诊断和 #064 的融合等待补证。

**接续（#094）**：#090 已完成三 idle epoch 和断流身份恢复出口；复用 adapter／plan_env／trace。正常融合推进与一次服务请求被保守拒绝分别分析，N06.3 核对当前 live query 缺口；目标任务中的持续新鲜度仍由 N09／正式任务交付。

**实施**：固定最终完整进程负载，区分 adapter 转发、EGO 收到、plan_env 实际融合和可用于规划四个时刻；记录源龄、接收龄、实际融合间隔、队列与资源。有限成对比较传输／调度，仅在证据支持时修改。

**出口**：至少 3 个 fresh epoch 的完整负载运行满足预先声明的诊断 freshness 门，无正常输入下长空窗或无界积压；断流关闭门、reset 确认后新身份重建正确。N09 及正式任务继续证明从目标前到结束满足相同融合要求，不能只用静止无目标窗口替代飞行。

**交付**：实际融合时序报告、必要修复及断流／重置验证。禁止用重发消息、增加缓存或修改源戳冒充新观测。

### N04 raw 地图几何、自由空间与未知空间验证

**依赖**：N01、N03。承接 raw 快照、#063 射线修复和早期多障碍几何证据。

**接续（#094）**：#091 已完成两布局诊断测量；复用布局、快照、投影和分类评估。原报告保留的表面漏分、false-free／false-occupied 与时序位移不是已解决项；仅在 N06 定位到相关缺陷或 N10 标准要求时补对应修复／回归，不另建地图。

**实施**：至少两种布局，包含墙、箱／柱、通道；在同一 epoch 采多时刻快照并回读。先用隔离 debug_truth 组合定位投影／射线问题，再以 VINS 位姿完成在线地图评价；两类结果分开保存。

**出口**：障碍位置／表面误差、厚度与重影、已观测覆盖、障碍漏检和错误 free、融合延迟都有可复算结果；验证障碍前 free、表面 occupied、遮挡后 unknown。记录 raw 与 inflation 的区别、体素边界和离散误差，不把最近表面残差小等同于整张地图正确。

**交付**：带 K／外参／stamp／epoch／map_id／配置哈希的多时刻快照、误差报告、输入异常验证。不得把完整世界几何输入在线地图。

## 第二组：使当前安全实现获得实际动作资格

### N05 起飞、地面、自身过滤与观测入口

**依赖**：N01、N04。承接 #065 仅证明远离起点的一个 0.5 m free 球；它没有起飞资格。

**接续（#094）**：#092 完成 no-go 入口诊断；复用完整 SDF 包络、唯一预算、五阶段规则和在线／离线检查。合法正向起飞／保持入口仍缺，交由 N06.3–N06.4 处理并重验受影响 N05 项；本任务历史 passed 不授权任何动作。

**实施**：从当前机体、桨、附件及相机安装 SDF 计算参考点和完整包络；结合定位／地图误差定义初始保守空间预算。明确自身过滤、允许的地面接触、起飞／降落接触阶段与其余必须已知 free 的区域；以未武装完整机体和固定相机验证能否实际获得必要观察。若涉及预扫描，明确执行方式及其向无支架起飞的迁移条件。

**出口**：起飞点、上升段、保持区和下降／接地区域有可执行的状态规则与在线检查，禁止区域不会被误清；至少两种布局的离线扫掠与未武装准入一致，物理飞行体积中的 unknown 或不足明确拒绝。整格位于经 fresh raw-ground plane 确认的保守地面下界以下的地下体素不属于飞行体积；地面相交／以上的 unknown 仍按 N05 contact 规则拒绝。未武装扫描通过不计飞行通过。不存在可实现的单相机入口时保留失败并调整合法流程，不能创造任意起点豁免。

**交付**：几何／坐标说明、唯一包络配置、规则实现、在线拒绝与地图快照对照。

### N06 完整曲线、重规划、停止与保持检查集成

**依赖**：N03–N05。承接 #062 目标球与 #064 patch0039 的真实 EGO＋合成深度组件证据，不重写同一算法。

**实施**：使用 N05 包络审查唯一占据谓词、整条活动曲线、末端 hold、紧急 hold 和重规划衔接；检查连续采样覆盖、资源上限、map_id 与 freshness。为 N07／N08 校准动作声明保守运动边界和完整已知区域。

**出口**：至少两种实际仿真布局、匹配地图快照中，物理飞行体积的全机体连续扫掠无 unknown／越界／禁止接触，地面以下空间仅按 N05 的已确认 ground boundary 排除；新障碍、迟到曲线、错误身份和查询失败都取消／拒绝。记录运行开销，不能只通过合成组件或中心线检查。动力学制动参数仍待 N08 实测，本任务不认证最终速度。

**交付**：集成修复、曲线／地图身份一致的证书与拒绝记录、校准动作的合法进入条件。

**接续顺序与当前状态（#101–#109）**：N06.1 query／offline candidate、N06.2部分组件与N06.3入口视场诊断已有证据。r26连续2°yaw保持health/map但body球仍有1,809 unknown；r27扩至15°后在truth yaw约9.852°触发`normalized_cost_exceeded`。r28 wall单轴X后退／回程保持健康，body／hold snapshot raw free；r29同布局actual EGO对`(0,+0.6,0)m`目标生成45-query `reason=free` B-spline，无fault／late curve。r30 corridor候选sweep及terminal hold含raw unknown，自定义目标未发送。r31的`−3.2m`回退撞上x=−3.0m后墙并触发定位失效；r32避墙但snapshot-03 source pose缺4.191s、live sphere service返回`no_fresh_fused_depth`，未发goal。r33 corridor和r34 wall使用0042及source-matched snapshot/live gate：每轮三张快照均精确匹配唯一source pose，body／连续sweep／terminal hold均raw free；EGO各生成一条B-spline，full-curve证书分别22 queries／0.219ms和45 queries／0.396ms，reason均为free。两次无fault且graph无控制出口；曲线未执行。完整记录见[#105](../progress/evidence/n06-corridor-observation-boundary-20261023-105.md)、[#106](../progress/evidence/n06-corridor-wall-clearance-20261023-106.md)、[#107](../progress/evidence/n06-corridor-wallclear-holdpoint-20261023-107.md)、[#108](../progress/evidence/n06-completed-fusion-sphere-gate-20261023-108.md)、[#109](../progress/evidence/n06-second-layout-live-ego-certificate-20261023-109.md)。

N06.8／r31的执行结果是明确 no-go，不是正向入口：−3.2m profile与x=−3.0m后墙碰撞，随后定位和MapStatus失效；snapshot与gate没有产出。保留相位持续时间支持和fail-closed目标门控。

N06.9／r32确认wall-clear运动profile和两张source-matched快照的raw body／sweep／hold，但snapshot-03缺4.191s source pose，live sphere service仍以`no_fresh_fused_depth` fail-closed；未提交goal。

**N06.10已完成（r33）**：0042使只读`QueryOccupancySphere`按已有完整曲线证书的语义读取最近完成融合；同epoch/map/frame、source/fusion age、pose gate与raw unknown／occupied／越界／query error拒绝均保留。输入recording由150延长到160 wall秒以覆盖实测source-pose gap，运动profile与`(0,+0.25,0)m`候选目标不变。三张snapshot source pose唯一匹配，snapshot／live body、连续sweep和terminal hold全raw free后，EGO full-curve证书通过并生成一条planner-only曲线；这不代表飞行或父目标完成，见[#108](../progress/evidence/n06-completed-fusion-sphere-gate-20261023-108.md)。

- **N06.3：入口 unknown 与 live readiness 分类诊断。** 先只读复算 #092／#093 和 wall-r10／corridor-r10，不重复已经失败且无新假设的扫描。对实际 VINS 起点的 body sphere／hold 体积逐格区分：未进入视野或近距盲区、机体遮挡、射线／分类缺口、地图边界、接地阶段规则或参考点不一致。用源时刻相机位姿／有效深度／raw 分类与 N05 几何解释首个拒绝及覆盖下界；完整世界几何只供隔离离线评价。分别核对 wall 的 `no_fresh_fused_depth` 与 corridor probe 缺 odometry，是服务对待处理输入的保守语义、真实融合过期、接收／QoS／启动窗口，还是其它有证据原因；不把 N03 的 idle 通过视为自动排除。交付“已证实／已排除／仍未知”、可观测性边界和一个主要变量的下一动作协议，不能只增加日志或延长等待。
- **N06.4（#121，已完成）：按定位结果最小修复与正向入口复核。** 仅在 N06.3 有新判别信息后，选择一项有证据的输入／射线／查询修复、与 N05 一致的阶段处理，或可实际执行的未武装观测流程。新流程先核对 VINS 支持运动，再做 fresh identity／释放后复检；修改按上表回归。不得清空 unknown、缩小既定预算、任意起点豁免、换成理想位姿／世界点云或用新控制器越过入口。若证据表明当前单 D435i／包络／合法观测流程无法提供入口，保留 N06 未通过并给出具体范围调整建议，不擅自更改验收。
- **N06.8：corridor入口局部地图窗口与hold复核（r31，已执行但未取得入口证据）**。r31启用分段时长、延长input recorder并加入三张source-matched snapshot与live body／sweep／terminal-hold守门。计划回退x=−3.2m撞上`n06_observation_surround`后墙（近面x=−3.00m）；夹具真值最低x=−2.987523m并漂到+2.011171m。随后VINS报告`normalized_cost_exceeded`、MapStatus不ready，snapshot-01 readiness超时；探针未运行且未发目标。详见[#106](../progress/evidence/n06-corridor-wall-clearance-20261023-106.md)。
- **N06.9：corridor wall-clear holdpoint（r32，运动与两快照正向谓词已证实，入口门控未通过）**。夹具真值最低x=−2.600431m、最终x=−0.803939m，避开生成后墙；所有记录的定位／depth-health均valid。snapshot-01/02 source pose唯一匹配，body／连续sweep／hold全raw free。snapshot-03 source stamp超出最后pose记录4.191s；live sphere service也返回`no_fresh_fused_depth`，故没有goal。详见[#107](../progress/evidence/n06-corridor-wallclear-holdpoint-20261023-107.md)。
- **N06.10：completed-fusion sphere gate（r33，已通过子项出口）**。0042只改pending读取语义，age、身份、pose及raw分类门不变；输入录制延至160s，运动profile不变。三个source-matched snapshot和live body／sweep／hold全raw free，full-curve certifier通过并生成一条planner-only曲线。运行报告与局限见[#108](../progress/evidence/n06-completed-fusion-sphere-gate-20261023-108.md)。

- **N06.2.1／r34 wall第二布局同门控planner-only集成已通过。** 三张source-matched快照和live body／24-query sweep／terminal hold均raw free，EGO 45-query full-curve证书free并生成一条曲线；与r33 corridor合计两布局。证据见[#109](../progress/evidence/n06-second-layout-live-ego-certificate-20261023-109.md)。
- **N06.2.2／#111 已通过其组件故障出口。** 隔离 EGO/plan_env＋synthetic depth 观察到 raw free／occupied／unknown／outside 分类、wrong-map 零查询拒绝、active-map-loss `full_curve_unknown`、completed-hold `full_curve_terminal_hold_occupied`，fault 后零迟到曲线。当前活动注入先被 unknown 拒绝；直接 occupied 路径由 #093 提供。#108 关联 bounded query/sweep 与 adapter identity/stale/timeout/late-reply/pending-cancel 回归。组件运行不代替实际布局证据，详见[#111](../progress/evidence/n06-active-obstacle-hold-refusal-20261023-111.md)。
- **N06.2.3／#112 实际布局双目标重规划交接已通过子项出口。** r35 sampled odometry age 为0.566s时 fail-closed且未发goal；不放宽0.4s门限，探针增加等待fresh同epoch里程计。r36三张source-matched快照分别认证+0.6m和+0.9m y两个目标，body／24或36-query continuous sweep／terminal hold均raw free；live gate两次均通过。EGO在同一epoch/map下生成traj_id 1／2两条证书free曲线，planner log明确`EXEC_TRAJ→REPLAN_TRAJ→EXEC_TRAJ`，零fault，control-free graph。曲线未执行；报告见[#112](../progress/evidence/n06-live-replan-handoff-20261023-112.md)。
- **N06.2.4／#113 已通过：组合身份／freshness／query／resource拒绝矩阵。** 错误epoch/map零错误曲线、stale depth／odom、raw free／occupied／unknown／outside／invalid分类、query/sweep resource bound、adapter timeout/busy/late/cancel及fault后零迟到曲线均有可追溯证据。隔离组件与r35布局拒绝分别标明，不相互替代。
- **N06.2.5／#116 已通过：emergency-hold补丁与故障出口。** #0043仅令raw地图障碍触发EMERGENCY_STOP并尝试通过同一freshness、identity、body和terminal-hold门的静止样条；stale／错误身份／查询资源失败仍fail-closed。#116 free hold发布成功；组件试验 #118 hold unknown拒绝；#119 stale拒绝；#120 completed terminal hold改变后通过认证的静止样条；均无迟到曲线。#115同路径peer未改变raw occupancy，未触发目标分支，保留为非通过诊断。
- **N06.2.6 已通过当前补丁版两布局复核。** #123 corridor +0.25m目标的三张source-matched snapshot与live body／10-query连续sweep／terminal hold全raw free，EGO 22-query证书耗时0.219ms；#122 wall的+0.6m及+0.9m目标分别通过三张source-matched snapshot和live门，EGO 45／61-query证书耗时0.544／0.624ms，并记录EXEC_TRAJ→REPLAN_TRAJ→EXEC_TRAJ。#121 +0.6m corridor在0.175s扫掠命中occupied而未发布目标曲线，作为实际布局拒绝证据。报告见[#116](../progress/evidence/n06-emergency-hold-fallback-20261023-116.md)。
- **N06.2.7／本轮 #118 实际布局动态 terminal-hold emergency-hold 已通过子项。** #124 的 +0.4 m X 目标因已有墙体使 hold occupied 被拒；#125 +0.4 m X/+0.3 m Y 基线证书通过，但大盒生成后定位健康门关闭、map_id 改变，EGO 以旧身份拒绝目标；#126 使用 0.15 m 立方体后，三张 snapshot 和 live baseline gate 通过，D435i 将障碍融合为 raw occupied，目标 hold occupied、当前位置 hold free；EGO 进入 `EMERGENCY_STOP` 并发布通过 fresh-map full-curve 证书的静止 hold 曲线。没有 PX4、controller、traj_server 或轨迹执行。详情见[本轮 #118 证据](../progress/evidence/n06-dynamic-obstacle-response-20261023-118.md)。
#094 中 N06.3 的地图覆盖与 readiness 诊断、N06.2 的 planner 集成由 #095–#123、#116、#118 与 #151 支持。此前缺少全机支架释放后的 N05 fresh admission；#121 已在 wall 和 corridor 两布局补齐。父 N06 现为 `passed`；当时 `execution_plan.next_goal=N07`。后续 N07 按累计三次标准通过，当前主线指针为 N08。#122/#123 使用 debug sensor rig 的限制仍保留；#151 提供当前 probe 的 wall 证书，corridor #123 所用 EGO／plan_env 与安全半径未受 N05 ground-boundary 改动影响。审计见[#117](../progress/evidence/n06-completion-audit-20261023-117.md)，完成证据见[#121](../progress/evidence/n06-ground-boundary-release-admission-20261023-121.md)。

#120/#145 历史结果：wall 全机扫描完成 12/12，释放后旧规则仍以 38 个地下 unknown 拒绝，详见[#120](../progress/evidence/n06-support-release-admission-20261023-120.md)。#121 按已验证 raw-ground plane 实现 whole-cell 地下排除：只在 fresh plane、PX4 landed 和起降垂直阶段生效；与保守地面下界相交或高于它的格子、HOLD unknown、地面未确认及越界仍拒绝，不生成 free rays，也未更改不确定度预算。

#146 wall 与 #148 corridor 均完成 12/12 全机支架扫描，before/after/post-release identity 连续；after 与 post-release N05 online/offline 五阶段检查均接受，最大 unknown 为 0，PX4 全程 DISARMED、bridge DISABLED、无控制／目标／真值输入。两次 fixture helper 都留下 `localization changed or became invalid during physical scan` 错误且 `outcome=failed`，尽管 12/12 阶段完成、最终 localization valid、N05 post-release gate 通过；wall remove service 有确认，corridor remove ack 缺失但 Gazebo model list 证实 fixture 不存在。该工具警告保留在运行摘要中，不能解读为飞行或全流程运行 PASS。相关细节和哈希见[#121 证据](../progress/evidence/n06-ground-boundary-release-admission-20261023-121.md)。


N06 原出口和 #094 增加的正向入口条件现均有证据，因此父 N06=`passed`。#152 corridor 因未取得 fresh VINS odometry 而在发目标前 fail-closed；#153 平移视角诊断在 `normalized_cost_exceeded` 锁存后中止；这两次未产生 planner 结果。当前 N06 planner 双布局证据由 wall #151 和 corridor #123 支持，后者的 EGO／plan_env 源码、补丁与 body/hold 安全半径和当前版本一致。所有曲线都只由 planner 计算并未执行；N08 仍负责动态制动和停止距离。N07 是下一依赖满足的主线目标，但本轮未启动。

### N07 当前版本 EKF2 融合与无目标悬停基线

**依赖**：N02、N03、N05、N06；先证实本次起降／保持区可用，再解锁。

**接续（#094）**：复用现有视觉里程计转换、时间映射、Offboard 状态机及起降流程。先只读核对本版本 frame／源时间／EV 配置和唯一发布者；N06 入口未通过时不开始飞行。原悬停与落地出口保持，不移植上游 SO(3) 控制器或 fake odometry。

**实施**：完整 VINS／地图／EGO 负载，无导航目标；核对相机 IMU→机体参考点、速度 frame、NED／FRD、局部原点／yaw、源采样时间及实际 EKF2 EV 融合。保持参考固定。

**出口**：同一固定版本累计 3 次独立冷启动通过，不要求连续；每次无目标空中保持至少 30 仿真秒，记录墙钟、独立定位和保持误差；无健康锁定、时间映射或控制丢失，真实 landed／disarmed。实际 ROS graph／PX4 参数／ULog 证明无 GNSS／真值辅助和唯一控制发布者。失败保留为失败记录，但不清除已通过的 run；已通过的 run 不复测。其余单次验收阈值不变。

**交付**：逐次 manifest、融合与轨迹报告、起降结果。历史 #054 三次 16 m 导航不替代当前安全版本本出口。

### N08 低速制动测量与 hold→EGO 连续切换

**依赖**：N06、N07。校准动作必须在事先检查的足够大已知区域内，先有保守运动／停止边界；若边界无法建立，不执行。

**接续（#094）**：复用 EGO 优化器、已有停止末端约束和 bridge；按 hold／仅计算／执行三方式取得判别证据，随后量测实际制动并补必要修复。上游恒定位置停止样条不能替代动态停止距离，三个重复目标和 N05／N06 预算回填仍必须完成。

**实施**：受控比较固定 hold、EGO 计算但桥保持、桥执行合法 EGO 曲线。对齐目标、样条、PositionCommand、PX4 设定点和独立运动；验证位置／速度／yaw 连续、轨迹有效时间、取消后的停止／保持。用低速独立校准量化响应延迟、最小可用减速度、实际停止距离和跟踪偏差。

**出口**：完成受控机制解释或针对性修复；同版本至少 3 次独立冷启动重复目标运行，参考与健康连续，实际停止／保持和落地成功。给出速度、观测距离、机体误差余量、延迟与制动之间的预算，回填 N05／N06；如改变包络或实现，重跑其受影响项。零位移可检查切换，不替代位移／制动证据；bridge 不生成未经检查的平滑或绕行段。

**交付**：受控对照、制动曲线、预算来源和相关修复。`time_forward` 的 yaw 前视不作为位置提前执行的既定根因。

### N09 三维目标、yaw、取消／替换与不可达反馈

**依赖**：N03、N06、N08。

**接续（#094）**：复用已有 action 与 goal／epoch／cancel／yaw 接口，从缺失的实际动作矩阵开始，不再新建任务系统。按下述出口同时核对简单航点、EGO、实际三维到达和飞行期地图连续性；不能恢复上游手动目标高度固定 1 m 或仅按轨迹时间判定实际到达的假设。

**实施**：同一候选版本验证简单航点与 EGO 共用控制出口，实际位移明显大于到达容差，覆盖高度变化、不同 yaw、活动任务取消／替换、超时和不可达／未观测目标拒绝；航向动作服从观测与机体旋转包络。

**出口**：至少 3 次独立冷启动的有位移目标重复通过，反馈与独立真实到达一致、目标前至任务结束融合持续新鲜、无违规接触；旧 goal／epoch／map_id 消息不影响新任务。不可达或未知目标明确终态，不盲飞或无限重试。当前阶段为诊断，不算 N11–N14 正式次数。

**交付**：动作矩阵、执行与拒绝报告、接口示例与必要修复。

## 第三组：冻结后逐项完成正式验收

### N10 单一版本、干净重建与定量标准冻结

**2026-10-28／#434 当前范围覆盖说明**：用户明确跳过当前N10.3的故障注入/故障后校准；下文旧计划中“故障退出校准”不再作为本轮必做出口。故障条款仍未验证、既有失败完整保留，不标passed或计N15正式次数。继续正常导航的定位/地图/跟踪/净空/重规划/资源标准，正常任务失败不因本排除项消失。#428已按用户取消仿真受控停止，不计原生landing通过。

**2026-10-27 剩余执行复核**：按用户要求以少重复、合并补采及离线验收为原则细化 [N10 当前计划](n10-completion-plan.md)。优先核对并复用 #381/#385 归档，不再为已有速度量测新飞；净空和故障路径仍需独立依据，未降低出口。N15 各类至少两次、N16 十分钟正式运行仍在冻结后；N10 只做冻结标准所需校准，不把正式矩阵全部提前跑。当前 N10.3/#389 保持，父 N10 未通过。本次仅规划，无新运行。

**依赖**：N01–N09。

**接续（#094）**：复用现有 fetch／build／manifest 与分享工具，审计同一上游基准和当前有效补丁链，而非重新迁入第三方或重做工程骨架。将 N02 的历史未解项、N04 的地图分类／时序风险、N05／N06 新观测的定位失败与所有受影响回归显式绑定最终支持范围；同步修正活跃说明中落后于 sources.json 的补丁顺序／构建状态，不能靠文档一致宣称运行通过。

**实施**：从固定来源干净 fetch／build，验证补丁重放、唯一 vendor／install 与有效参数；为重建后身份完成受影响回归。建立单一验收配置，写明定位／地图／跟踪误差、机体净空、时距／速度、到达、源龄、融合、重规划和故障边界的值、理由及测量方法。

**出口**：各项有独立校准依据和可执行判断器；GOAL F 的默认到达起点为 ≤0.30 m、≤15°、≥3 s，其余门限不能凭成功片段反推。对 N02 未解历史问题作明确适用范围与回归决策；支持范围不足则先修复。冻结源码／binary／配置／环境指纹，之后才开始正式任务。若回环未进入生产，定位预算以 raw VIO 为准。

**交付**：冻结配置、理由／覆盖矩阵、构建日志与哈希。正式运行后影响结果的变更使相关正式次数重新开始。



**2026-10-27 N10.3/#380–#381 更新**：#380按同一`[0.60,0.66]m/s`水平触发窗口完成第3次独立caller-cancel量测：触发0.601626m/s、停止带进入5.116仿真秒、真值水平路径1.349452m；三次路径均值1.356701m、跨度0.032780m。该统计仅描述该三组状态，不是通用制动保证。#380 raw VINS只覆盖35.948仿真秒/4.186m。当前#381在补齐原始VINS线速度观测：只读recorder记录上游`estimator.Vs`世界系速度，离线用固定scale=1对齐和0.2仿真秒中心差分对照Gazebo IMU真值；任务配置保持#376不变。当前runtime-contract为`547082a4538a871dd3c3b9b26c0f6b45369fa18bf1b73a8d93f219ef3e537cce`。协议及prelaunch身份已冻结，SITL待启动；N10仍`in_progress`。
**总体计划（#333）**：N10.1/#334、N10.2/#335完成，当前N10.3。#357完成16m目标和600仿真秒ACTIVE保持，raw VIO位置p95 0.497m/yaw p95 8.692°，EGO跟踪p95 0.521m，source/occupancy age最大0.164/0.100s；Goal F位置和yaw同时在限值内持续243.28仿真秒。#359在实测PX4速度0.50024m/s触发caller-cancel，真值停止路径1.30447m；#362在当前gate-free runtime以0.50018m/s触发，停止路径1.26099m、进入停止带6.76仿真秒（#359为4.96秒）。两次高速量测的距离和时间有差异，不能作一般制动保证。SDF/真值分析#357/#359/#361的采样净空扣除相邻样本包络运动后分别0.42859m／1.38836m／0.33791m，连续动力学间距仍未证明。项目自加的VINS质量与定位/里程计回执龄运行门限已从仿真运行路径删除，cost与源龄仍记录；时间戳/会话完整性、地图身份/新鲜度、PX4桥控制完整性和official_ego碰撞保持。旧 `acceptance_calibration_limits` 仅是未执行的配置字段，已清理。#361 当前 gate-free runtime 冷启动已完成 16m/3D/yaw 与 600 仿真秒 ACTIVE 保持；独立真值最小位置误差0.053m、位置+yaw同时驻留3.019s；raw VIO位置误差p95/max 0.314/0.323m、yaw p95/max 5.691/5.854°；EGO跟踪p95/max 0.502/1.031m；normalized cost p95/max 1.255/3.271且没有锁存；map source/occupancy age max 0.160/0.112s。五观察器终态、禁止接触0、PX4独立落地读回均通过。#362本身量测完整、禁止接触0、五观察器终态覆盖和独立安全读回通过；#361当前SDF静态净空经#363离线复算，扣除观测到的相邻样本包络运动后为0.33791m，但不构成连续动力学证明；#362未单独复算净空。两轮均没有动态障碍注入和PX4闭环重规划证据，故障退出边界也未测。详见[#361](../progress/evidence/n10-health-gates-removed-speed080-16m-20261027-361.md)、[#362](../progress/evidence/n10-cancel-stop-gatefree-speed050-20261027-362.md)与[#363](../progress/evidence/n10-clearance-static-world-replay-20261027-363.md)。0.15m tracking、0.4s age不是正式限值；raw VIO误差/漂移、地图几何、净空误差余量、重规划及故障时限仍缺最终依据。N10.3继续收敛标准及适用范围。#364协议已用于#365单次PX4动态障碍SITL：箱体ACK与传感器表面观测、后续几何绕行轨迹均出现，但native EGO后续一次优化仍失败，项目0039立即中止逻辑使任务未到点；该run零违规接触并安全落地，动态箱体离线采样净空扣减后0.949m。#366按用户授权增加补丁0053，移除项目自加整曲线准入调用并恢复EGO上游规划失败重试；17 ROS包构建通过。#367实际复测中，障碍创建ACK、表面观测和后续轨迹均出现，但目标因bridge的`external_odometry_stale`降落而`goal_timeout`；VIO样本晚0.296s仿真（约0.345s墙钟）仍在0.35s源龄上限内，却超出64个`/clock`样本历史，时间映射拒绝。箱体采样净空调整后0.982m、零违规接触，安全落地读回通过；导航和完整VIO误差评估未通过。#368把clock mapping历史从64增至128，23项时间映射单测通过；同场景SITL没有再报映射错误，但因项目自加0.15m translation对齐门（实测0.181539m）触发降落、目标`goal_timeout`。方箱ACK、D435i/EGO观测和后续样条出现；扣减最大相邻样本运动后采样净空0.920173m，禁止接触0，安全落地读回通过。用户授权后已删除项目自加translation/yaw数值对齐拒绝门，诊断值保留；415项测试与ROS集成、17包构建通过。#369已运行：action成功并保持600仿真秒，但机体与静态`unit_cylinder_4`有134条接触记录，不能作为无碰撞通过。#370固定SE(3)复算显示首次接触时EGO参考到真值IMU偏差0.51874m；未保存圆柱ROI相机/occupied点云，不能确认地图漏检。旧到达窗口直到action成功时联合驻留2.759523墙钟秒；延至落地的N10窗口为267.040仿真秒，包含action返回后的保持，N10.4需统一任务反馈窗口。#371先按用户要求删除bringup中四项项目自加N05数值几何拒绝，再重建并只增强圆柱接近时的相机、occupied-cloud ROI与同身份raw occupancy查询。当前飞行参数值不变；415项测试、17包ROS构建通过，runtime身份更新为`9c2f704d…9b6ede6`。SITL尚未启动。N10.3仍缺量化依据、重复性与故障边界。详见[#360](../progress/evidence/n10-calibration-synthesis-20261027-360.md)、[#365结果](../progress/evidence/n10-live-obstacle-replan-20261027-365.md)、[#366修改](../progress/changes/2026-10-27-366-n10-remove-custom-curve-check.md)、[#367协议](../progress/evidence/n10-live-obstacle-replan-retry-protocol-20261027-367.md)和[#368结果](../progress/evidence/n10-live-obstacle-clock-history-result-20261027-368.md)。


**2026-10-27/#374–#375 更新**：#372/#373均在目标提交前失败并保留为无飞行记录，#373错误为只读报告引用已移除的接收龄摘要键；两次均独立读回LANDED/disarmed/control-disabled/zero-control后安全停止。#374删除审计确认的项目自加定位valid/TRACKING状态门、DepthHealth门和16有效像素门；保留epoch/frame/time身份、PX4原生preflight/EV融合、EGO上游碰撞/输入watchdog和唯一控制桥。构建17包、415项测试及两项ROS集成通过。#375协议绑定当前runtime `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7` 与5m horizon/0.8m/s/0.25m/s² profile，待运行；N10.3尚缺定量理由、重复性和故障边界证据。

**2026-10-27/#375–#376 更新**：#375实际spawn为默认x=-6.5m，而协议要求x=-8m；本次不计作协议飞行。run仍显示动态方箱插入ACK及替换样条，但action因上游EGO报告terminal point occupied而`goal_timeout`，真值最小目标误差1.392m；目标约在x=9.60m，距房间内墙0.323m，低于0.731m规划膨胀半径。0违规接触，末态独立读回安全并停止。#376已准备好显式planner与spawn配置，并在driver中校验加载路径、来源哈希和pose。详见[#375错配报告](../progress/evidence/n10-live-obstacle-cylinder-spawn-mismatch-20261027-375.md)；#376首个driver预检因prelaunch缺少顶层planner_config_path字段退出，未发送目标；PX4/bridge独立读回仍落地、未武装、控制关闭、零控制。现已补字段并绑定prelaunch SHA，保留同一栈重跑预检。
**2026-10-27/#384–#386 更新**：#384 动态障碍观察器因协议缺少 `injection` 段而在未发 goal/enable、零控制状态安全中止，按无飞行准备失败保留。#385 在修正协议后完成 PX4 SITL 诊断：唯一飞行变量是 native dwell=4.0 仿真秒，独立 GOAL F 判据仍为位置≤0.30m、yaw≤15°、连续≥3.0仿真秒；最长联合窗口3.320仿真秒，action成功，600仿真秒ACTIVE hold、零违规接触和落地上锁读回通过。该结果为单次诊断，不是正式资格。动态箱体注入 ACK、占据ROI与trajectory ID变更可见，但离线轨迹净距依赖未经确认的坐标假设且计算含零净距；只报告观察，未证明绕行。整机净空采样下界扣除观测样本间位移后为0.118m，仍不是连续动力学证明。#385原总driver因离线分析器缺少 `ground_rotation` 字段退出1；#386在保留旧输出基础上补充v2到达报告与post-run分析，6项到达边界测试通过。N10.3继续处理坐标对齐、连续净空、故障退出和负载数据；N10.4–N10.7未完成。见 [#384](../progress/evidence/n10-arrival-dwell-setup-abort-20261027-384.md)、[#385](../progress/evidence/n10-arrival-dwell-calibration-result-20261027-385.md)、[#386](../progress/evidence/n10-arrival-simtime-analyzer-compatibility-20261027-386.md)。

**2026-10-27/#387 更新**：固定prestream SE(3)表明协议预计的方箱odom中心与SDF world中心偏差0.264m；用精确SDF world箱体重算后，整条B样条几何仍有箱体内采样点，但按时间戳对齐的实际READY PositionCommand中心线距箱体至少1.463m。真值全机包络采样扣除观测样本间位移后下界1.131m，且零违规接触；只是单次采样。箱体中心附近注入后0.5/1.25仿真秒的同身份raw-map query均返回free=160、occupied=0；存档occupied ROI来自静态圆柱观察，不关联箱体。故实际轨迹采样绕开箱体，但不能证明是地图占据触发，query/map更新语义需先审计。见 [#387 复核](../progress/evidence/n10-obstacle-alignment-forensics-20261027-387.md)。

**2026-10-27/#388 更新**：源码审计确认 #385 的 0.25m raw sphere 完全在动态箱体内部，离迎机面约0.272m；`/mapping/query_occupancy_sphere` 检查 raw occupancy cells，不含 inflation。EGO 原生优化器与碰撞回调使用 inflated occupancy，射线融合只标记可见返回端点及其前方 free traversal，不填充箱体内部。因此内部 `free=160` 单独不能诊断表面漏检；但#385没有保存箱体表面 occupied 点坐标或同刻 inflated point-query，动态障碍是否真正被表面观测并驱动绕行仍未确认。无代码／飞行改动。详见 [#388 审计](../progress/evidence/n10-raw-versus-inflated-occupancy-audit-20261027-388.md)。

### N11 空场正式三连

**依赖**：N10。**实施**：最终视觉组合空场 3 次独立冷启动；完整起飞、实际目标、到达、降落／上锁。**出口**：3/3 成功、零碰撞，全部冻结指标达标，保留失败。**交付**：三个正式 run 与程序化报告。

### N12 单障碍正式三连

**依赖**：N11。**实施**：起终点直连被单障碍阻挡的布局，实际 EGO 绕行，3 次独立冷启动。**出口**：3/3 成功、零碰撞，完整机体与实际跟踪净空达标；由只读接触／几何评估证明绕障。**交付**：布局身份、匹配快照、候选／实际轨迹与三个正式报告。

2026-10-29/#500：用户取消10秒平移RPE P95≤0.05m否决条件，N12起使用revision10配置，仅报告平移RPE实测与覆盖，其余验收项保留。#498原正式飞行按新规则完整重评PASS，旧FAIL保留；校准不倒算为正式次数。

2026-10-29/#508：用户取消地图表面误差0.1m数值否决，revision11保留实测/支持检查；实际机体净空0.1m、零碰撞和地图分类仍保持。已有正式归档按新规则完整重评，旧报告保留。

2026-10-29/#519：N12限定出口通过；9次正式飞行中累计3次独立合格，#494/#502/#506/#509/#512失败和#504不足保留。详见[完成审计](../progress/evidence/n12-final-completion-20261029-519.md)。

### N13 错位多障碍正式三连

**依赖**：N12。**实施**：错位多障碍布局 3 次独立冷启动，记录在线更新和重规划。**出口**：3/3 成功、零碰撞，未知策略、数据新鲜度、净空和重规划期限符合冻结值。**交付**：完整指标与地图／轨迹证据。

2026-10-29/#520：N13起移除最小机体净空0.1m数值否决，采用[revision12](../config/acceptance_n13.json)，保留量测/完整覆盖/零违规接触，其它标准不自动取消。[附加规则核对](n13-project-restrictions.md)。本次无飞行，N13仍not_started；场景/重规划协议须显式绑定新配置，不沿用旧10cm筛选。

2026-10-29/#536：N13按用户#521功能策略及#533证据处理修正版完成，#531/#534/#535同运行版本独立GUI冷启动3/3。逐柱路线、地图更新和实际执行重规划、到达/接触/正常终态与身份全部通过；独立VIO/地图/资源及密集几何按批准仅诊断。历史revision12条目仅溯源，不作为当前门。见[完成审计](../progress/evidence/n13-final-completion-20261029-536.md)。

### N14 可通行窄道正式三连

**依赖**：N13。**实施**：按 N10 包络与误差预算确定可通行宽度，3 次独立冷启动。**出口**：3/3 成功、零碰撞，实际机体净空达标；N11–N14 组合至少一次高度变化与不同 yaw。不可通行／未知目标另有明确拒绝或超时，不计为正常场景成功。**交付**：通行条件、全部正式 run 和不可达验证。

2026-10-29/#546：N14按#521功能策略完成2.4m净宽/6m长通道三次独立GUI正式任务（#541/#542/#543），及#545占据/遮挡raw未知但planning占据目标的真实拒绝。未知本身按原生策略允许；未新增已取消数值门。所有会话安全停止，三份报告及负目标详见[完成审计](../progress/evidence/n14-final-completion-20261029-546.md)。

### N15 六类故障的检测、退出和最终运动

2026-10-29/#547：用户明确“不用处理故障情况”，本项排除，不执行且不标passed；原协议如下保留追溯。N16/N17不再依赖本项，现有运行机制不删除。

**依赖**：N10；推荐完成 N11–N14 后执行。按冻结的故障场景与可接受边界开展，必要时先完成该注入的非飞行预演。

**实施**：双目断流、相机 IMU 断流、深度断流、VINS 重启、规划器退出、时钟回退，分别至少 2 次独立注入；可按一类故障分多轮完成本任务。

**出口**：12 次以上注入各有触发→检测→轨迹失效／制动或退出→PX4 最终状态；量化定位失效降落漂移与实际净空，满足冻结边界。新 epoch 取消目标／轨迹并清图，无自动续飞；Offboard loss 按既定超时 Land，禁止自动重进。发送 Land 不算结果通过。

**交付**：逐故障报告和汇总，保留失败／中断。

### N16 连续 5 分钟完整负载任务

**依赖**：N11–N14；N15按用户#547排除。**实施**：冻结版本连续至少 5 仿真分钟（用户#552，300秒，替代原十分钟），包含实际飞行任务和重规划；记录墙钟、RTF、CPU／内存／队列、端到端延迟、定位与地图误差。**出口**：无崩溃、持续失控或无界积压，全部适用冻结指标合格，最终正常落地上锁。单次短任务拼接、纯静止或只运行 VINS 不计。**交付**：完整资源／时序曲线及任务报告；不外推机载实时能力。

**2026-10-29/#568完成**：N16由#566真实GUI连续325.108sim秒、6段独立到达、零违规接触、正常终态及完整资源/地图/时序审计通过。初始缺参考及其同运行原生恢复、保守误差复算、历史失败保留，见[最终报告](../progress/evidence/n16-final-completion-20261029-568.md)。只资格化#565隔离走廊版本；历史N11–N14不自动外推到新gyro校准版本，N17需核对受影响回归/交付身份。

### N17 A–H 回收与可重建交付

**依赖**：N11–N16。

**实施**：逐项核对 A–H 和 P0–P6；回归 G 的独立接口调用程序；回读地图／关键帧，整理构建、启动、目标、取消、降落、停止、故障及限制文档，清除活跃文档中早期实现状态的冲突。重启交付示例并核对 N10 固定版本；如重建造成有效实现／参数变化，重跑受影响验证。

**接续（#094）**：复用现有 project.sh／start.sh、地图／关键帧与独立评估程序，补齐最终结果和版本限制；不另造启动器。交付说明区分上游复用、本地补丁、已验证仿真支持范围及 H0–H5 实机待办。

**出口**：`progress/evidence/FINAL_ACCEPTANCE.md` 引用全部正常／失败／中断正式 run 与哈希；A–H、P0–P6、S1–S6 及 N01–N17 有各自适用的通过证据。用户可按交付入口重建并运行示例；不擅自提交、上传或推送。

**交付**：最终报告、可重建清单、操作文档、准确的已支持范围和实机待办。

## 可选研究与后续实机

### R01 回环平移／yaw 鲁棒核耦合的有界离线验证

对应旧待确认 #078：先复现 #077，再只拆分共同 Huber 残差块，比较位置和 yaw；保留预先约定的完整接受条件，不只选择改善项。得到肯定或否定结论都可结束该研究问题；不修改生产链路，不因此关闭定位或飞行任务。本次重写不启动该实验。

### R02 回环候选的跨 epoch 收益与在线使用决策

仅在决定扩展任务时距或 raw VIO 预算不足时排期。候选须在多 fresh epoch 对比位置／yaw、错误回环、资源和时延；先作独立观察。即便离线通过，在线使用仍须另行落实连续 odom、map→odom、目标转换、地图重积分与轨迹取消等契约，并重跑 N01–N17 受影响项。不能直接把跳变修正位姿接入旧地图／PX4。

回环研究允许与主线穿插，不自动成为主线依赖；若证明当前要求必须依赖它，应记录依据并显式修改依赖和回归范围。

H0–H5 的真实 D435i、机载平台、时间域、安装外参和实机阶段见[完整路线](simulation-to-hardware-roadmap.md)。当前 GOAL 仍验收仿真；硬件信息、真实设备操作与飞行授权另行明确，仿真通过不替代实机证据。
