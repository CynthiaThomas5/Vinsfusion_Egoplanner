# #117 N06 完成状态审计

日期：2026-10-23。范围：复核 `codex resume --last` 恢复的 N06 Goal 完成任务。此报告是状态审计，不是新的运行通过证据。

## 结论

N06 planner 集成子项有通过证据，但 **N06 父目标不能标为 passed**。当前状态应为 `in_progress`，`next_goal=N06`。

N06.2 的实际布局曲线证书、重规划交接、故障拒绝、紧急 hold 与资源开销记录继续有效，参见 [#116 综合报告](n06-emergency-hold-fallback-20261023-116.md) 和 [#113 拒绝矩阵](n06-freshness-identity-resource-refusal-20261023-113.md)。#121 的实际 occupied 拒绝也保留。审计没有撤销这些 planner 结论。

阻止父目标通过的条件来自 #094 的 `remaining_exit_rule`：N05 的 `passed` 仅代表 no-go 诊断，N06 在 N07 前还必须建立合法正向入口，并满足原有 N06 出口。N05 证据明确记录 wall-r03 与 corridor-r01 的全机支架扫描因 raw unknown 拒绝；wall-r05 的 1.0 m 扫描在释放后复检仍 `transfer_gate_passed=false`。详见 [N05 入口报告](n05-entry-20261023.md)。

## #122/#123 不构成合法正向入口

两次运行的 planner 证据是真实 Gazebo、D435i、VINS、plan_env/EGO 地图上的有效 planner-only 结果，分别位于 wall 与 corridor 布局；但传感器运动来源与 N05 全机支架释放流程不同：

- `tools/prepare_motion_world.py` 从 world 移除 `sensor_fixture` 的固定关节和原模型 include，然后重建仅含 D435i link、`gravity=false` 的移动诊断 rig。
- `tools/run_sensor_motion.py` 用 Gazebo `EntityWrench` 增量驱动该 rig，记录 truth/IMU 供诊断；其输出 scope 明确为 `Physics force-driven debug sensor rig; no truth feedback or PX4 control`。
- 两个 runner 均在观测动作停止后采集地图，再由无控制的 probe 提交 planner-only goal。它们没有 X500 全机、N05 支架 attach/detach、PX4 DISARMED 状态或释放后 N05 在线 admission。

因此这些记录能够证明在给定实际传感器地图和当前 planner 门下，曲线会通过或拒绝；不能证明一条合法的全机起飞／保持入口，也不能解除 N05 no-go。

| 运行 | Planner 结果 | 关键归档 |
| --- | --- | --- |
| #121 corridor | +0.6 m 目标的完整扫掠在 0.175 s 命中 occupied，正确拒绝发布曲线 | `artifacts/runs/n06-20261023-corridor-121/`；probe SHA-256 `cbc9f5b027424d981132a077a1eea8dceec9aaca76febee615cc0ac72f578de9` |
| #122 wall | +0.6 m 与 +0.9 m 双目标均通过快照和 live body/sweep/hold 检查；记录 replan handoff | `artifacts/runs/n06-20261023-wall-122/`；probe SHA-256 `834f3a0e72f392fe53456ea9817f14866beded93f01ae164c250e7d6a1216639`；run-input SHA-256 `7bb50d1ef603b65bbee779722e985bc94a24c7c9e6c6fc144203d4120ec0ec96`；motion SHA-256 `d63b7dfb29f5f0f8523369dd999a7e6718508d83367bfa23b02d13009593f6da` |
| #123 corridor | +0.25 m 目标通过快照和 live body/sweep/hold 检查，EGO full-curve 证书为 22 queries／0.219 ms | `artifacts/runs/n06-20261023-corridor-123/`；probe SHA-256 `7232cc74a28cece8cf2c35df4b6c1205a425aa992a2ca7299a7095a92ee04fec`；run-input SHA-256 `137f069b68cf86d916254fb3faf26dbb239eb017ad6ea15c5886c2d03f935b5a`；motion SHA-256 `0f7a81f5d057a3571a6581060cc1fcde8b58131fede99a7d96d0bed99589f378` |

生成器哈希：`tools/prepare_motion_world.py` 为 `e83fbacb80f9e57ec892ef06161bd29bade2f72477f917210b8afc71b537dd5e`；`tools/run_sensor_motion.py` 为 `8b9b1262843cc9ceaf7b057355079e90883002db23ca3478140d156521f98e84`。两次运行的 mapping log 哈希分别为 #122 `bd148474f75df69eaed656a10395f987024ae31f2787ab47452d7d518d8cfc54` 和 #123 `310db88745482d23aa3dee8d0220eab9e357bbd8f2665a63f5dba1b5f7b1cb14`。

## 当前执行边界和下一步

当前恢复的 N06 运行范围禁止启动 PX4、桥、控制器、traj_server、导航监督器和轨迹执行。N05 的全机支架释放后 admission 流程要求在线确认 DISARMED 状态并在释放后重跑准入；因此当前范围内没有可产生这项证据的执行路径。不能用诊断 rig 的 planner-only 通过替代，也不能改 unknown、包络或 N05 阶段门。

下一子项保留为 **N06.4：完整机体的未武装观察流程及释放后 fresh admission**。恢复执行需先明确 N06 是否允许运行 N05 释放复检所需的 PX4 DISARMED 状态链；如授权范围仍禁止该链，保持 N06 未通过，不启动 N07。获得入口证据后，再复核受其影响的 N05 出口和当前补丁版 N06 双布局 planner 证书。动态制动和最终速度仍由 N08 验证。

未启动新的仿真、构建、测试或飞行会话。项目结构状态检查和文档一致性命令记录在 [#117 改动记录](../changes/2026-10-23-117-n06-completion-audit.md)。
