# GOAL C 第二障碍布局连续机体包络审计 #383

- **任务摘要**：继续把 GOAL C 从中心线诊断推进到机体包络和同刻占据快照审查。
- **用户约束**：保留所有既有工作区修改；单 D435i / P0–P6 范围；truth 仅用于隔离调试；bridge 是唯一 PX4 控制发布者；本轮不把离线分析或 planner-only 输出说成飞行验收。
- **决定**：复用 #321 已封存的第二障碍布局、两条完整 spline 与配对 NPZ 快照；使用 #246 审计过的 0.4819358707 m x500+D435i 方向不变包围球，并按连续采样间隔上界检查 unknown/free/occupied/inflation/out-of-map。
- **结果**：两条 full-active sweep 均未碰到 raw occupied voxel，但分别包含 1,342/1,241 个 unknown、937/841 个 inflation voxels 和 141/153 个唯一地图外 voxels。两条碰撞 AABB 都延伸到 map z 最低边界 -0.15 m 以下约 5.3–5.5 cm。模型包络不能分类为已知自由；未执行轨迹。
- **待决问题**：本地 odom 的地面高度和有效起飞高度相对 map z 下界如何对应？下一次 full-envelope 复测应在哪个可证据化的空中起点进行？
- **证据**：[报告](../../progress/evidence/p2-ego-dense-sphere-sweep-audit-20261021-383.json)、[运行清单](../../artifacts/runs/p2-ego-dense-sphere-sweep-audit-20261021-383/run-manifest.json)、[完整分析](../../artifacts/runs/p2-ego-dense-sphere-sweep-audit-20261021-383/body-sweep-analysis.json)。
