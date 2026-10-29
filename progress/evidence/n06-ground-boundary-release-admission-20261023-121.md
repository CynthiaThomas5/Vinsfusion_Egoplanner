# #121 N06.4 地面边界与释放后准入完成报告

日期：2026-10-23。父目标：N06；执行范围：N06.4 地下体素边界、wall/corridor 全机支架释放后准入，以及当前补丁版 N06 planner 出口复核。结论：**N06 在 planner 集成范围通过**。本报告不表示起飞、飞行或整个仿真 GOAL 通过。

## 地面以下的空间规则

用户指出地下区域不属于可飞行空间。当前规则只在 fresh raw-ground plane 有效、PX4 确认 landed 且处于 TAKEOFF_CONTACT、ASCENT、DESCENT 或 LANDING_CONTACT 时，将整个上表面位于保守地面下界以下的 voxel cell 排除出碰撞分类。地面拟合残差和半 voxel 边界 allowance 都纳入下界；不合成 free ray，也不清除地面以上或相交格子的 unknown。

HOLD unknown、地面未确认、过期输入、地图外及与地面边界相交或高于边界的 unknown 仍 fail-closed。机体半径、hold 邻域半径和 uncertainty budget 均未缩小。#145 旧地图在当前策略下离线重放接受全部入口阶段；其历史 online 结果仍是旧规则下的拒绝，因此 `matches_online_result=false`。新的 #146/#148 运行分别重新执行 online 和 offline gate，结果一致。

## 全机支架释放后 N05 准入

| Run | Layout | 扫描与状态 | 释放后 N05 online/offline | 新鲜度与身份 |
| --- | --- | --- | --- | --- |
| #146 | `wall_box_column` | 12/12 阶段；PX4 DISARMED、bridge DISABLED、landed；没有控制、目标或真值输入 | 两者 `accepted=true`, `all_entry_phases_known_and_clear`；TAKEOFF_CONTACT、ASCENT、HOLD、DESCENT、LANDING_CONTACT 最大 unknown 均为 0 | epoch/map_id 从扫描前到释放后不变；snapshot/source/fusion 分别 0.088/0.124/0.032 s，门限 0.4 s |
| #148 | `corridor_box_column` | 12/12 阶段；PX4 DISARMED、bridge DISABLED、landed；没有控制、目标或真值输入 | 两者 `accepted=true`, `all_entry_phases_known_and_clear`；五阶段最大 unknown 均为 0 | epoch/map_id 从扫描前到释放后不变；snapshot/source/fusion 分别 0.112/0.088/0.028 s，门限 0.4 s |

两轮都从 raw occupied voxels 拟合到 z≈−0.35 m 的 ground plane，扫描后与支架释放后均重新取图、复验姿态与身份；释放后 online 和 offline 报告相互匹配。两次都不是自由飞行，也没有启动导航控制。

运行 helper 的 `fixture-result.json` 在两轮都记录 `outcome=failed` 和 `localization changed or became invalid during physical scan`，虽然已完成 12/12 阶段、记录的最终 localization valid、run summary 的 `diagnostic_pass=true`，且 post-release N05 gate 完整并通过。wall 的 fixture removal service 有确认；corridor 的 remove ack 缺失，但 Gazebo model list 确认场景中已无 fixture。两项 helper/cleanup 警告均保留，不按全流程运行 PASS 解读；它们不改变单独采集的 released-state N05 gate 结果。

运行原始文件及 SHA-256：

- #146：`artifacts/runs/n06-20261023-wall-146/`；run summary `ac7ad949e4c63744327240a84f71b625f5888385650624815cfeb491d2c2ed67`；fixture result `11af54df655f0d5b40e4d14053ed73240ffd48f93eae6d0070d6cfd741ab4ac8`；post-release online `e5ced5e78bce9890fd4039cd8d629965afdf2a15f132ab62b1785a2a9f5a46ff`；offline `17137a067ccfcfea29eda72987c276b712b3c2f3eaf2d1c98eab33cae8ea1a74`。
- #148：`artifacts/runs/n06-20261023-corridor-148/`；run summary `ea48d5afe031aacdada9f9cd8f5f147d020f5ed928b61e703f22c5dc5a0ca62a`；fixture result `8e38ff68b358df7285f092dc330709e22f5794124fb33b2d292d00f673cbe7ae`；post-release online `761b603c8eda13160ca4c44af9efc957759266b00c109e61f6b70d12ba7daf2b`；offline `ee4e224cf833f5502f61936c0937c93d47e536200e13191efe9e357ca8634be6`。

## N06 planner 出口与当前版本对应

- Wall #151 使用当前 `tools/probe_n06_live_layout.py`（SHA-256 `8c90741621fcac95680891d7c22526810b9c84a588d7c4ab38beb1993a67a11a`）。三张 source-matched 快照、实际 VINS 位姿 body sphere、24-query continuous sweep 和 terminal hold 均通过。首条曲线为 45-query `reason=free` 证书、0.440 ms；第二目标再次通过三张快照及 live 门，58-query `reason=free` 证书、0.864 ms。planner log 记录 `EXEC_TRAJ → REPLAN_TRAJ → EXEC_TRAJ`；无 planner fault、无迟到曲线，graph 没有控制节点或控制 topic。
- Corridor #123 的三张 source-matched 快照、live body/sweep/hold 均通过，10-query sweep；EGO 22-query `reason=free` 证书、0.219 ms，无 fault 或迟到曲线，graph 无控制出口。
- #123 的 probe hash 与 #151 不同，是后续有界 handoff 日志采集改动；它未改变单目标准入。两轮的 EGO／plan_env 代码与 #0039、#0041、#0042、#0043 补丁哈希一致。N05 新增的地面阶段规则不进入 N06 planner 查询；当前 `body_reference_clearance_radius_m=0.7306179170842027 m` 和 `terminal_hold_neighborhood_radius_m=0.25 m` 与 #123 有效值相同。因此 corridor 单目标 planner 证书仍匹配当前 planner 实现与预算。

此前的 planner 拒绝／停止证据继续有效：#113 身份、新鲜度、查询资源及故障拒绝矩阵；#116 有净空时认证静止 hold；#118 wall 实际地图障碍被 raw map 检出后，目标 terminal hold occupied，EGO 进入 `EMERGENCY_STOP` 并发布已认证静止 hold；#121 的 +0.6 m corridor 曲线因 occupied 正确拒绝。所有曲线都只由 planner 计算，没有接入 controller 或执行。

#152 corridor 在提交 planner goal 前没有 fresh VINS odometry，故 fail-closed；#153 平移视角运行在 `normalized_cost_exceeded` 锁存后安全中止。两轮没有 planner 结果，作为失败诊断保留，不替代 #123 证书。#147 的早期 corridor 视角 profile 也因 `telemetry_stale` 在第 4/12 阶段结束。

## 验证与状态

- `python3 tools/test_n05_entry.py`：10 passed。
- `python3 tools/test_vehicle_envelope.py`：3 passed。
- `python3 tools/test_preflight_scan.py`：19 passed。
- `python3 tools/test_sim_geometry.py`：5 passed。
- `python3 tools/audit_vehicle_envelope.py`：通过；几何、ground-contact 与唯一包络配置一致。
- `bash -n tools/run_n05_preflight_layout.sh tools/run_n04_map_layout.sh tools/run_n04_map_layout_container.sh`：通过。
- `python3 -m json.tool config/components/navigation/vehicle_envelope.json`：通过。
- #146/#148：两个独立全机支架释放后 fresh N05 live SITL gates 均 accepted；两轮保持 DISARMED 且无控制出口。
- #151/#123：当前 wall planner 与兼容的 corridor planner 证据通过；未执行曲线。

因此 N06 原 planner 集成出口及 #094 增加的合法正向入口条件都有证据，`progress/milestones.json` 中 N06 标记 `passed`，`execution_plan.next_goal=N07`。N07 保持 `not_started`，不属于本轮范围。整个 GOAL、P6/S4 和 A–H 仍未通过；动态制动和实际停止距离归 N08。完整改动见[本轮改动记录](../changes/2026-10-23-121-n06-ground-boundary-semantics.md)。
