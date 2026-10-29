# FAST Lab 官方起飞与未知空间规则（#331）

用户于 2026-10-26 明确要求采用高飞团队官方规则，暂不引入第二颗相机。本页覆盖旧 N05/N06 文档中的 raw-known-free 导航前置；历史数据和失败不改写。N09 限定出口已按 #332 通过：repeat01、repeat02、repeat04 三次独立冷启动通过，repeat03 因原有定位健康门触发而安全失败并保留。N10 仍需审计、校准、干净重建和最终版本冻结。

## 固定官方依据

- Fast-Drone-250 commit `8ff64274b161bb829653faf5946656658e7e2c9f`：[官方操作流程](https://github.com/ZJU-FAST-Lab/Fast-Drone-250/blob/8ff64274b161bb829653faf5946656658e7e2c9f/readme.md#第十一章ego-planner的实验)先自动起飞，再启动 EGO 发送目标。[PX4CtrlFSM](https://github.com/ZJU-FAST-Lab/Fast-Drone-250/blob/8ff64274b161bb829653faf5946656658e7e2c9f/src/realflight_modules/px4ctrl/src/PX4CtrlFSM.cpp)检查 odom、静止≤0.1m/s、landed 和 RC 条件；自动起飞保持水平位置和 yaw，按给定垂向速度上升到高度后悬停，无 raw-map 起飞净空查询。教程包含飞手接管流程，不证明完全自动盲区安全。
- ego-planner commit `bfda51284c8c1b476043255a8145ef925a3778a5`：[grid_map.cpp](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/plan_env/src/grid_map.cpp)保持 raw unknown，inflated occupied buffer 初始 0，检测到 occupied 后才膨胀置 1。[grid_map.h](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/plan_env/include/plan_env/grid_map.h)的 `getInflateOccupancy` 返回 inflated buffer（越界 -1）；[optimizer](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/bspline_opt/src/bspline_optimizer.cpp)使用这一谓词。unknown 本身不是 inflated occupied。
- 本项目仍使用唯一已固定的 ego-planner-swarm ROS2 基准 `23a8d5a191711dd65633df689bd00f55d4dea8f9`，按补丁 0049 适配上述规则。没有引入另一份 planner/ROS1 控制栈。

完整参考文件、URL、commit、SHA256 位于 `artifacts/runs/n09-official-policy-331/official-source-manifest.json`。它们仅作只读来源，不加入在线控制。

## 当前规则

唯一选择位于 `config/components/navigation/task_supervisor.json` 的 `collision_policy=official_ego`；launch 将它传为 `grid_map/official_ego_collision_policy=true`，导航和 runner 读取同一来源。

| 环节 | 当前行为 |
| --- | --- |
| 独立起飞 | 定位结构/身份有效、PX4原生preflight及EV融合有效、着地未武装、控制关闭；起飞前0.1m/s经验速度拒绝门已移除。bridge垂直起飞并按其完成条件进入ACTIVE。无 N05 五阶段 raw-free/地面拟合/支架扫描门。 |
| 导航开始 | EGO/map 进程可预先启动并保持无目标（本 ROS2 适配将 mapper 放在同一进程），实际目标仅在 bridge ACTIVE/armed/airborne/control-enabled 后转发。起飞期间 EGO 不接管垂直设定点。 |
| 目标 | ROS2 action 使用 `/mapping/query_planning_occupancy` 的零半径点查询，直接读同一 inflated predicate；raw unknown 返回 `unobserved_not_occupied`，与 `free` 分别标示。 |
| 轨迹 | 原生 EGO 优化、inflated occupied 碰撞与在线重规划继续执行；项目附加的 raw-known-free 全曲线与终点/应急保持球认证不在官方模式执行。 |
| raw 数据 | `/mapping/query_occupancy_sphere` 与 snapshot 仍原样区分 unknown/free/occupied，不清起点、不伪造 free rays，不把规划可通过写成已观测空闲。 |
| 故障/身份 | ROS2 时间/epoch/map 绑定、定位/深度结构与会话完整性（质量/源龄/回执龄只读）、取消/超时反馈、独占 bridge 和自动 Land 退出为本项目集成契约。未引入 RC 时由单一 bridge 服务授权；不会假称有官方 RC 飞手。 |
| 参数与模型 | 保留当前 X500+D435i 的真实尺寸、安装外参、低速试验参数及配置 inflation；不照抄 250mm 飞机的数值。新增传感器与模型变更不在本次范围。 |
| 评价 | 实际飞行由 PX4 控制；独立真值/接触仅作评估。位移、到达、接触、持续 freshness、落地上锁各自判定，unknown 放行不等于净空证明。 |

当前标准启动会默认生成只读 contact overlay；`project.sh n09 RUN` 与普通 `project.sh mission RUN PROFILE` 共用此规则。N08 专项 raw-capsule/braking runner 保留为旧策略实验，不自动应用到当前导航。

## 验证与适用范围

需验证：unknown 仍是 raw unknown，同时官方 point predicate 可通过；occupied/inflated occupied、越界、错误 epoch/map、过期仍拒绝；地面合法 unknown 目标不得在起飞前转发；ACTIVE 后才可进入 EGO；取消旧目标与反馈仍正确。旧 known_free 单测与 ROS integration 使用显式历史配置，不将其“unknown 必拒绝”结论套用到 official_ego。

官方流程未提供后方盲区的自动全向安全证明，本项目也不作此声明。本次是用户授权的策略变更；N05/N06 历史 pass 保留原策略适用范围，当前 N09 与 N10 版本冻结另取证。

## #348 用户授权的速度保护调整

用户明确要求开放前述额外速度限制。当前导航runner移除本项目0.12m/s reference/PX4双源自动取消门，改为只读速度观测；0052补丁移除N08取消停车总速0.10m/s和垂向0.01m/s准入拒绝。原生规划max_vel/max_acc机制及现有身份/故障契约保留；起飞前0.1m/s静止拒绝门已取消，桥起飞完成的速度0.2m/s条件单独处理。这些改动不代表较高速度制动已通过测量；历史N08/N09证据保留原身份。

## #520 当前源码核对

以上当前表格按实际源码纠正了遗留的起飞前0.1m/s门描述。N13起取消离线最小机体净空0.1m；航向跟踪0.10rad/s补丁、膨胀半径0.7306m等项目取值未随之改变。完整[附加规则清单](n13-project-restrictions.md)区分上游机制、项目在线分支和离线验收门，不能把项目数值称为统一官方标准。
