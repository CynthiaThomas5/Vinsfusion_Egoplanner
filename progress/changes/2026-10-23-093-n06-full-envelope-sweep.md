# N06 全机包络扫掠续接与 no-go 记录

对应对话：[2026-10-23-093 N06 接续](../../collaboration/dialogues/2026-10-23-093-n06-resume.md)。用户显式恢复 N06，继续 Goal 完成模式；N06 保持 `in_progress`，不修改 GOAL 验收契约。

## 本轮改动

- 将 `config/components/mapping/ego_planner.json:ground_height_m` 与 `config/components/navigation/vehicle_envelope.json:required_map_bottom_m` 调至 -1.0 m，使地图边界覆盖 N05 body sphere 加 0.25 m terminal hold neighborhood。`vio_ego_bringup.py` 解析时强制校验完整半径；对应 vehicle envelope 和 resolver 测试更新。raw unknown 仍拒绝。
- 新增 `tools/probe_n06_live_layout.py`：在真实 Gazebo+VINS+plan_env/EGO 图内读取地图身份、新鲜度、实际 VINS 起点球与 EGO 样条／故障；图中检查 PX4/bridge/controller/setpoint 缺席。仅发布到 EGO planner goal topic，不存在任何控制订阅者。
- `tools/run_n04_map_layout.sh` 与容器 runner 增加明确 `motion_n06` 模式、EGO 节点发现等待和 planner-only probe；普通 `motion` 仍保持 N04 map capture 行为。当前配置的双布局最终 raw replay 使用 wall-r10 与 corridor-r10 的 static captures。
- `tools/run_sensor_motion.py` 保持原始四轴 profile 默认调用，增加可选六轴角运动 profile；`config/components/simulation/n06_observation_sweep.json` 用作一次性诊断。对应 wall-r09 在 map freshness gate 关闭后由 runner SIGINT 安全停止，不能用作有效快照。
- `tools/analyze_n06_snapshot_sweep.py` 增加 analyzer 自身哈希，并明确离线候选链永远不能声明 N06 positive exit。`tools/probe_ego_safety.py` 的 after-completion 注入改为让障碍只碰 hold neighborhood，用于检查 terminal hold 拒绝。
- 更新[N06 证据报告](../evidence/n06-full-curve-layout-review-20261023.md)、[机器可读报告](../evidence/n06-full-curve-layout-review-20261023.json)、[CURRENT](../CURRENT.md)及[milestones](../milestones.json)。

## 运行和验证

- `bash tools/project.sh build ros`：17 packages finished。
- `bash tools/project.sh test`：243 tests passed；navigation adapter integration 检查通过。
- 合成 full-curve probe：通过；活动证书 61 queries / 0.528 ms，wrong map identity、unknown、planning failure 均拒绝，late curve 为 0。
- 合成 after-completion probe：通过；活动证书 61 queries / 0.567 ms，终端 hold 证书 61 queries / 0.543 ms 并拒绝 `full_curve_terminal_hold_occupied`，late curve 为 0。
- 当前 planner/policy 组合的两布局分析：`python3 tools/analyze_n06_snapshot_sweep.py --run-id n06-20261023-wall-r10 --run-id n06-20261023-corridor-r10 --output artifacts/runs/n06-map-sweep-20261023-r04/report.json`；所有快照身份和 freshness 有效，但 body/hold 球均有 raw unknown，两个布局候选中心数均为 0。
- wall-r10 live EGO probe：identity 稳定、无控制图；query 返回 `no_fresh_fused_depth`，EGO 返回 `full_curve_planning_failed`，0 样条、0 late curve。corridor-r10 收齐三张有效快照，但 probe 在 10 秒内没有收到 VINS odometry，没有发送 goal。
- Python 编译、profile shape、runner `bash -n` 与 `git diff --check` 通过。`python3 tools/project_status.py`：PASS（结构一致性检查，不代表 SITL）。

## 限制与下一步

N06 出口仍缺两布局实际 EGO 全机连续扫掠、terminal/emergency hold 和 replanning handoff。较早的 wall motion snapshot 发现一条离线候选链，但起点不在实际 VINS pose，且紧急保持扩张在末段遇到 unknown；corridor 没有终端保持体积。这些都不能证明 N06 通过。

停止原因：两布局当前配置的起点 body/hold 球 fail-closed 于 raw unknown；wall live query freshness 也失败，corridor live probe 缺 odometry。N06/S4 保持 `in_progress`，`next_goal` 仍为 N06。下一子项 N06.3 需在不改变未知拒绝策略和 N05 预算的前提下，找出单 D435i raw occupancy 起点/保持体积缺失原因；有有效两布局 live EGO 曲线后再做完整回归。PX4、bridge、实机和 flight 均未启动。
