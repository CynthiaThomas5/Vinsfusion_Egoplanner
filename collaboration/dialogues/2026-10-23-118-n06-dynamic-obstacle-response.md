# N06 动态障碍响应

- 日期与任务 ID：2026-10-23／#118。
- 用户目标：通过 `codex resume --last` 恢复 Goal 完成模式，继续推进指定目标 N06。
- 本轮范围：补充 N06 原始动态障碍出口的实际布局证据。只运行 wall 布局的 D435i、VINS、plan_env 与 EGO planner；不启动 PX4、桥、controller、traj_server 或导航监督器，不执行曲线。
- 已有基础：#121 已证明实际布局 occupied 目标被拒绝；#122／#123 已证明两布局 static-map 的 source-matched snapshot、body／sweep／hold 和完整曲线证书；#116 已验证 synthetic active-map obstacle 的紧急 hold 逻辑。N06 父目标仍因 #094 合法正向入口规则未满足而 `in_progress`。
- 首次运行 `n06-20261023-wall-124` 的结果：三张 snapshot 与 live body/sweep 通过，但原 wall 物体已使 +0.4 m X 目标 terminal hold raw occupied；goal gate 正确拒绝，未发布曲线、未创建注入物。该次没有检验动态响应。
- 基于该失败，离线复算三张快照上的候选。`(+0.4,+0.3,0) m` 在 body、连续 sweep、terminal hold 上均 raw free；目标 hold 球与拟注入盒体几何相交，注入点 query 基线三轮均 raw free。
- `n06-20261023-wall-125` 使用该目标偏移，三个 snapshot 与 live body/sweep/hold 通过，并生成一条 planner 曲线。注入 0.3×0.3×0.6 m 盒体后，mapping log 记录 `normalized_cost_exceeded`；同 epoch 下 map_id 改变、MapStatus 关闭，EGO 记录 `full_curve_map_id_mismatch`，转 `WAIT_TARGET`，零迟到曲线。未观察到目标 obstacle raw occupied，也未取得 emergency hold；这只证明 health/map identity 门的 fail-closed 结果，动态障碍响应出口未通过。停止阶段 VINS 与 mapping adapter 报 exit -11，Gazebo 在 runner 的 SIGINT／SIGTERM 清理后被 SIGKILL；需与运行内 gate 事件分开记录。
- 新假设：#125 的突然视觉变化使定位门锁存；将唯一主要变量“盒体尺寸”从 0.3×0.3×0.6 m 缩小为 0.15 m 立方体，保持颜色、位姿、运动、目标偏移和新障碍注入时序不变。相同几何离线复核显示，注入查询点距小盒最近角约 0.106 m（查询半径 0.12 m），目标 hold 球与小盒相交、完整 body 球仍留有净空。下一运行 `n06-20261023-wall-126` 检验定位门是否保持打开且地图／EGO 按目标 hold occupied 进入认证静止 hold。
- 预期证据：D435i 在线融合将障碍点登记为 raw occupied；起点完整 hold sphere 保持 raw free、目标完整 hold sphere 变为 raw occupied；EGO 记录活动曲线被地图阻断并转入 `EMERGENCY_STOP`，只发布通过同一地图证书的静止 B 样条。任何 B 样条仅被观察，不转发给执行器。
- 运行 ID／ROS domain：#124／114（基线目标拒绝）；#125／115（健康门锁存并 fail-closed）；#126／116（小盒动态响应试验待执行）。profile 分别为 `n06_x_dynamic_hold_obstacle.json`、`n06_xy_dynamic_hold_obstacle.json` 和 `n06_xysmall_dynamic_hold_obstacle.json`。
- 结果：#126 使用 0.15 m 立方体后通过本子项：三快照与 live body/sweep/hold baseline 通过；新盒 raw occupied；当前位置 hold raw free、目标 hold raw occupied；freshness 和 map identity 稳定；EGO 记录 `terminal_hold_occupied` 并进入 `EMERGENCY_STOP`，发布 2-query／0.066 ms、reason=free 的静止 hold；无 fault、无非静止曲线。完整证据见 [#118 报告](../../progress/evidence/n06-dynamic-obstacle-response-20261023-118.md)。
- 下一步：#118 planner-only 子项已完成。N06.4 全机支架释放后 fresh admission 仍是父目标出口条件；当前范围不允许启动该流程所需的 PX4 状态链，故 N06 仍 `in_progress`、`next_goal=N06`，不进入 N07。

本摘要保存任务范围与判据；通过证据只记入对应 `progress/evidence` 报告。
