# #121 N06.4 ground-boundary semantics 与 N06 完成

对话摘要：[N06 ground-boundary 对话](../../collaboration/dialogues/2026-10-23-121-n06-ground-boundary-semantics.md)。验收报告：[N06.4 完成证据](../evidence/n06-ground-boundary-release-admission-20261023-121.md)。

## 目标与已有基础

恢复 N06 Goal 完成范围。此前 N06 planner 出口已经有两布局证书、重规划、障碍故障拒绝与 emergency-hold 证据，父目标只因 N05 全机支架释放后入口被地下 unknown 阻挡而未关闭。用户确认地下区域不属于可飞行空间。

## 改动

- `tools/n05_entry.py`：引入 raw-ground plane 保守下界对完整 voxel cell 的判定。只有 fresh 地面平面、PX4 landed、TAKEOFF_CONTACT/ASCENT/DESCENT/LANDING_CONTACT 阶段下，cell 整体低于保守下界时才从飞行体积分类中排除。
- `config/components/navigation/vehicle_envelope.json`：记录地下 cell 排除阶段、边界 allowance、地面确认与 unknown 规则；body clearance、hold 邻域和 uncertainty budget 未缩小。
- `tools/test_n05_entry.py`、`tools/test_vehicle_envelope.py`、`tools/test_preflight_scan.py`：覆盖新地面边界规则与配置契约。
- 运行 #146 wall 和 #148 corridor：全机支架扫描各 12/12 阶段；DISARMED、bridge DISABLED；释放后 online/offline 五阶段 gate 均 fresh 且 accepted。两个 fixture helper 仍报告 `localization changed or became invalid during physical scan`，但最终 localization 有效、gate 完成；corridor removal acknowledgement 缺失但 Gazebo model list 确认 fixture 不存在。详细结果及哈希见 #121 evidence。
- 运行 #151 wall 当前 planner probe：三张匹配快照、live body/sweep/hold、目标和 replan handoff 证书通过。以既有 #123 corridor planner 证书复核兼容性：N06 的 EGO/plan_env 与补丁不变，ground-boundary 改动未改变 planner body/hold 半径。#152/#153 保留为 VINS health fail-closed 诊断，没有提交 planner goal。
- 更新 GOAL 现状描述、CURRENT、N01–N17 计划和 milestones：N06=`passed`（planner integration scope），下一指针 N07；N07 保持 `not_started`。不修改 GOAL 的验收契约或 A–H、P/S 状态。

## 验证

- `python3 tools/test_n05_entry.py`：10 passed。
- `python3 tools/test_vehicle_envelope.py`：3 passed。
- `python3 tools/test_preflight_scan.py`：19 passed。
- `python3 tools/test_sim_geometry.py`：5 passed。
- `python3 tools/audit_vehicle_envelope.py`：通过。
- `bash -n tools/run_n05_preflight_layout.sh tools/run_n04_map_layout.sh tools/run_n04_map_layout_container.sh`：通过。
- `python3 -m json.tool config/components/navigation/vehicle_envelope.json`：通过。
- `python3 tools/project_status.py`：最终运行 PASS。工具另外提示 80 个可选历史 artifact links 缺失；这些是报告的 optional links，不构成结构错误。
- `git diff --check`：通过。
- `config/runtime.json` SHA-256 恢复为 `a862e521dd738dba71d960cda95458509336f1e2cd845228b46311fd57928221`；当前没有 N05/N06 项目容器运行。

## 结论与限制

N06 额外正向入口条件和原 planner 集成出口都已取得证据，因此父 N06 完成。地下排除只改变物理飞行空间对真实地面以下 cell 的处理；不清除 unknown，不扩大可飞行空间，不意味着当前可以起飞。

所有 EGO 曲线均为 planner-only 输出，没有 controller、traj_server、bridge 控制出口或曲线执行。#146/#148 fixture helper 警告和 #152/#153 定位健康失败保留为限制。N08 仍需实测动态制动和停止距离；GOAL、P6/S4、A–H 仍未完成。N07 是下一项，但不在本轮范围。
