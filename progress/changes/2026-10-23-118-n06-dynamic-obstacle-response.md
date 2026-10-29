# #118 N06 动态障碍响应补充证据

- 日期：2026-10-23。
- 执行模式：用户恢复的 Goal 完成模式；指定父目标 N06。
- 对话摘要：[N06 动态障碍响应](../../collaboration/dialogues/2026-10-23-118-n06-dynamic-obstacle-response.md)。
- 证据报告：[N06 动态障碍报告](../evidence/n06-dynamic-obstacle-response-20261023-118.md)；[机器可读结果](../evidence/n06-dynamic-obstacle-response-20261023-118.json)。

## 改动

- `tools/probe_n06_live_layout.py`：支持 profile 锁定的动态 Gazebo 盒体注入；以 source/fusion age≤0.4 s、epoch/map/frame/readiness/reset-ack、raw obstacle occupied、当前位置 hold free、目标 hold occupied、`EXEC_TRAJ→EMERGENCY_STOP` 和 certified stationary hold 作为通过判据。运行后将诊断计数名改为 `post_transition_curve_count`，避免把正常的 emergency-hold 发布描述为迟到轨迹；#126 原始代码哈希保留于 run inputs 和 JSON。
- 新增 `config/components/simulation/n06_x_dynamic_hold_obstacle.json`、`n06_xy_dynamic_hold_obstacle.json`、`n06_xysmall_dynamic_hold_obstacle.json`：分别记录原目标基线拒绝、扩大后视觉变化导致 health gate 关闭，以及 0.15 m 小盒动态 hold 试验。每个运行使用单独 profile 哈希。
- `progress/evidence/n06-dynamic-obstacle-response-20261023-118.md/json`：记录 #124–#126 的运行顺序、通过谓词、SHA-256、失败结果与限制。
- `progress/CURRENT.md`、`GOAL.md`、`docs/remaining-small-goals.md`、`progress/milestones.json`：登记 #118 planner 子项结果；N06 仍 `in_progress`、`next_goal=N06`，N06.4 正向入口保持未通过。

## 结果

- #124：三张 snapshot/live body/sweep 通过；目标 terminal hold 被现有 wall 占据，goal gate 正确拒绝，未发布目标曲线、未注入盒体。
- #125：目标偏移 (+0.4,+0.3,0) m 的基线证书通过；0.3×0.3×0.6 m 盒体创建后，mapping 记录 `normalized_cost_exceeded`，MapStatus 关闭且 map_id 改变；EGO 以 `full_curve_map_id_mismatch` 转 `WAIT_TARGET`。没有障碍 raw-observed 或 emergency hold 证据。
- #126：三张 source-matched snapshots、live body/sweep/hold、EGO full-curve 证书通过；0.15 m 盒体被 raw occupancy 看作 occupied；当前位置 hold raw free、目标 hold raw occupied；MapStatus age 为 0.065/0.099 s；EGO 由 `EXEC_TRAJ` 转 `EMERGENCY_STOP`，发布通过 2-query／0.066 ms free 证书的静止 hold B-spline。无 planner fault、无非静止曲线、ROS graph 不含控制节点／控制 topic。曲线未执行。
- #126 probe 的 `passed=true` 且运行图与日志产物存在。运行收尾时 mapping adapter 报 exit -11；该报错发生在探针通过后的 runner shutdown。最初执行 shell 缺少 `set -e`，几何预检断言失败后仍启动了授权的 #126 运行；运行期间按正确 world→odom 高度换算复核了查询几何，没有重复启动。

## 验证

- Python AST、JSON profile invariants、map-frame injection-query geometry：通过；查询点距小盒最近角 0.106 m，小于 0.12 m。
- `bash -n tools/run_n04_map_layout.sh tools/run_n04_map_layout_container.sh`：通过。
- `bash tools/run_n04_map_layout.sh n06-20261023-wall-124 wall_box_column 114 motion_n06 config/components/simulation/n06_x_dynamic_hold_obstacle.json`：实际布局运行，基线 gate 拒绝；无动态注入。
- `bash tools/run_n04_map_layout.sh n06-20261023-wall-125 wall_box_column 115 motion_n06 config/components/simulation/n06_xy_dynamic_hold_obstacle.json`：实际布局运行，健康门关闭后 fail-closed；动态证据未通过。
- `bash tools/run_n04_map_layout.sh n06-20261023-wall-126 wall_box_column 116 motion_n06 config/components/simulation/n06_xysmall_dynamic_hold_obstacle.json`：probe JSON 中 dynamic response `passed=true`；runner 产生 snapshot、probe、ROS node/topic 和 mapping log 产物。探针运行哈希 `3e3933fa6bf97f635814aad30b4730e4beac1d014101f55450badff0129d93bb` 与 #126 `run-inputs.json` 一致。
- #126 关停后 `docker ps` 无本项目容器；独立 `volant-height-route-probe` 与 `natfrp-service` 未触碰。

## 未解项与下一步

未解：N05 合法正向入口／完整机体 support-release 后 fresh admission。当前 N06 范围禁止启动 N05 复检需要的 PX4 DISARMED 状态链，故 #118 不改变父目标状态，也不授权 N07。下一子项 N06.4 需要该运行范围解除后执行，并复核受影响的 N05 与当前补丁版双布局 N06 证据。动态制动与停止距离仍属于 N08。

停止原因：#118 动态地图障碍 planner-only 子项达到判据；父 N06 保持未完成，继续由 N06.4 出口约束。
