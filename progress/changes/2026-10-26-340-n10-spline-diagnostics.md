# N10 #340 spline feasibility diagnostics

对话摘要：[2026-10-26 N10 #340 样条诊断](../../collaboration/dialogues/2026-10-26-340-n10-spline-diagnostics.md)。

## 本次子项

沿 #337/#339 最终 spline feasibility 拒绝边界，增加只读量测，不改变规划门限、控制量、轨迹或refine上限。预登记协议见[报告](../evidence/n10-spline-dynamics-diagnostic-protocol-20261026-340.md)。

## 代码变化

- 新增 EGO patch `0050-n10-spline-feasibility-diagnostics.patch`：逐轴输出最大速度／加速度、当前 limit、tolerance、速度 ratio、加速度 ratio、总 ratio。
- 将最终 spline `checkFeasibility` 调用改为显示现有违反向量，并记录 refine 序号与当前限值。拒绝逻辑和比值计算保持原算法。
- 将 patch 顺序、应用上下文、补丁 SHA-256 和两个物化文件 SHA-256 登记到 `dependencies/sources.json`。

## 验证、局限与下一步

## #340 结果

- `bash tools/project.sh build ros`：17/17 包完成，28.1 秒；仅 `ego_planner` 有弃用接口和未使用参数警告。
- `D435I_N08_MODE=execute D435I_N09_CONTACTS=1 D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon2_calibration.json bash tools/project.sh sim n10-20261026-340-spline-dynamics-diagnostics`：项目 SITL 启动。
- `docker exec d435i-n10-20261026-340-spline-dynamics-diagnostics bash /workspace/tools/n09_runtime.sh n10-20261026-340-spline-dynamics-diagnostics config/components/navigation/n10_long_range_vio_calibration_goal.json n10_calibration`：runner 按预期因 `planner_full_curve_planning_failed` 返回 exit 1；没有 READY 样条。40 条汇总行显示 X 控制点速度 max 0.239385m/s > 0.1051门限；加速度 max 0.0449998m/s² < 0.2626门限。完整报告见[#340](../evidence/n10-spline-dynamics-diagnostic-20261026-340.md)。
- `python3 tools/debug_truth/evaluate_odometry.py artifacts/runs/n10-20261026-340-spline-dynamics-diagnostics`：exit 0；只覆盖 28.748 sim-s／1.893m 起降路径，最大定位误差 0.01386m。
- `bash tools/project.sh stop n10-20261026-340-spline-dynamics-diagnostics`：exit 0；随后只读确认容器 `exited 0`，PX4 arming_state=1、bridge LANDED/disarmed，违规接触 0。

## 局限与下一步

当前证据确认失败的动力学判据是 X 轴速度；不代表实际 PX4 飞行速度。日志还显示原 refine ratio 将“无加速度超限”哨兵 `max_acc=-1` 误算出 2.0，使 #340 首次总 ratio（2.0）高于速度项单独 ratio（1.90426）。下一子项 #341 将只修正未超限项对时间重分配 ratio 的贡献，保留原门限和拒绝判据，再按同一 mission 参数做一次新鲜 SITL；若未解决，依据新量测决定后续，而非重复调速。
