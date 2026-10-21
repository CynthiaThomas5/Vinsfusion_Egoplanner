# 修改与验证记录

- 任务 ID／日期：GOAL C canonical retry cooldown 与 dense spline guard #327 / 2026-10-21。
- 对话摘要：[2026-10-21-002 对话摘要](../../collaboration/dialogues/2026-10-21-002-p2-ego-canonical-retry-cooldown.md)。
- 修改文件：新增 `artifacts/runs/p2-ego-dense-spline-canonical-retry-cooldown-20261021-327/` run-local canonical source copy、patch 0028 overlay、构建与运行脚本、双次快照和离线分析；新增 [#327 轻量证据](../evidence/p2-ego-dense-spline-canonical-retry-cooldown-20261021-327.json)、本记录和对话摘要；更新 `progress/CURRENT.md`、`progress/goal-checklist.json`、`progress/evidence/README.md`、`dependencies/patches/ego/README.md`。未改 `src/vendor/ego_planner`、`dependencies/sources.json` 或 milestones。
- 行为变化及原因：canonical #297 pinned-source reconstruction 上按 0029/0030/0031/0028 顺序叠加，5包 Jazzy Release build通过。planner-only运行在1.0秒重试冷却下共60.346秒观察到519次 final-spline unknown拒绝、558个 replan headers；运行归一拒绝率8.60/s，较 #326 的444.79/s低约52倍（不同epoch和传感器样本，描述性比较）。两轮各输出2条 B-spline并成功捕获4份 snapshot；全部首2/3时域采样known-free且无inflation命中。第二轮的一条完整 spline末尾1/3仍有35个inflation-mask命中，最近occupied voxel-box距离0.47924 m，比名义0.482 m球半径少2.76 mm，故这是明确的待处理风险。
- 验证类型：源码重建与 patch dry-run、Jazzy Release编译、两轮Gazebo live planner-only仿真、同epoch只读快照及离线曲线分析；非PX4 SITL／实机验收。
- 命令与环境：`patch --dry-run -p1 < dependencies/patches/ego/0028-global-plan-retry-rate-limit-experiment.patch`；`bash artifacts/runs/p2-ego-dense-spline-canonical-retry-cooldown-20261021-327/build-ego.sh`；`bash .../run-container-snapshot.sh` 与 `bash .../run-container-snapshot-02.sh`；`python3 .../analyze_spline_snapshot.py`、`python3 .../analyze_spline_snapshot-02.py`。5/5包完成；两次 runtime均目标就绪、2 spline、2个接受快照；ROS图真值topic/控制topic/控制节点均为空。
- 结果及证据位置：见 [#327 轻量验收报告](../evidence/p2-ego-dense-spline-canonical-retry-cooldown-20261021-327.json) 和目录 `artifacts/runs/p2-ego-dense-spline-canonical-retry-cooldown-20261021-327/`。#326 canonical unknown guard 单独证据见 [#326报告](../evidence/p2-ego-dense-spline-canonical-unknown-guard-20261021-326.json)。
- 未验证与 PROVISIONAL：known coverage仅0.596–0.633%；snapshot start偏差0–73 ms、深度源龄69–132 ms；0.5 m inflation是轴对齐cube，未冻结。4条曲线只做centerline/voxel box离线比较，没有车辆扫掠、控制执行、跟踪误差、制动距离、PX4 SITL、真值评估或实机；不得以35个末尾命中之外的3条clear曲线推导安全性。GOAL C/D/F及A–H整体验收仍pending。
- 下一步：在 canonical + 0028/0029/0030/0031隔离链上新增全active-spline guard实验，重复相同planner-only场景并用逐 spline快照确认整个active curve已知且不命中inflation；如无可行样条，则如实记录fail-closed，不放宽阈值。

未提交；保留工作树中已有用户修改，本轮无暂存或提交。
