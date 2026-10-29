# #340 N10.3 最终样条动力学量测：X 轴速度主导拒绝

结论：**已查明 #337/#339 同类规划拒绝的直接约束项；N10.3 仍未通过。** 在 planner 的最终 B 样条控制多边形检查中，X 轴速度超限；实测加速度均低于检查门限。任务未发生水平目标运动，没有长程 VIO／地图／净空／跟踪或 600 秒保持证据。

## 数值结果

- 仅加入 diagnostics-only patch 0050；重建后 EGO 实际加载 `planning_horizon=2.0 m`、`max_vel=0.10 m/s/axis`、`max_acc=0.25 m/s²/axis`、容差 `0.05`。有效逐轴门为速度 `0.1051 m/s`、加速度 `0.2626 m/s²`（配置值 × 1.05，再加 `0.0001`）。
- 收到 40 条逐轴汇总检查、10 次最终规划拒绝。最终 refine 的最大控制点导数绝对值为 `vx=0.239385`、`vy=0.002076`、`vz=0.066659 m/s`；X 超过门限 `0.134285 m/s`，是明确拒绝项。这里是 B 样条导数控制多边形上的上界量测，不是 PX4 实际飞行速度；飞机没有水平起飞段。
- 最大控制点二阶导数绝对值为 `ax=0.0449998`、`ay=0.0002615`、`az=0.0070201 m/s²`，均低于 `0.2626 m/s²` 门限。没有加速度越限。
- 初始 refine 的 velocity ratio 为 `1.90426`；三次 refine 后该速度比升至 `2.39385`，峰值速度从 `0.190426` 增至 `0.239385 m/s`，依然未通过；planner 没有发布 READY 曲线。目标在 `0.096` 仿真秒／`0.0975` 墙钟秒后返回 `planner_full_curve_planning_failed`。

## 发现的 reallocation ratio 哨兵问题

EGO 原有 `checkFeasibility()` 在本次没有任何加速度越限时保留 `max_acc=-1`；随后 `sqrt(fabs(max_acc)/limit_acc)` 得到 `2.0`。因此日志中的 `acceleration_ratio=2` 是现有时间重分配公式的哨兵值副作用，不是实测加速度超限比；初次总 refine ratio 被抬到 `2.0`，而速度约束单独给出的 ratio 是 `1.90426`。这不会改变拒绝判据，但会改变 `reparamBspline()` 的时间重分配系数。下一步将只修正“未触发的分量不应贡献 ratio”这一处计算，保留 velocity／acceleration 检查、限值、容差和最多 3 次 refine，再做一次同任务单变量验证；不以此宣布成功，也不盲目提高速度。

## 安全与范围

- Preflight、official_ego 起飞准入、EGO graph 身份、接触传感器和 live terminal-refusal 探针通过。最终没有 READY trajectory，独立到达驻留失败属预期失败结果，600 sim-s hold 未开始。
- 接触评估通过，违规接触 `0`，观察到落地。PX4 `arming_state=1`、bridge `LANDED`／disarmed；项目容器随后以 exit `0` 停止，未触碰无关容器。
- 固定单次 SE(3) 的只读 VIO 评估覆盖 `28.748` 仿真秒和 `1.8931 m` 起降路径：位置误差 max `0.01386 m`、yaw max `0.03953°`，436 个配对样本，无 invalid localization。该段不代表 16 m 航程。
- `/clock` 无倒退，最大正源间隔 `0.104 sim s`；localization status 最大源间隔 `0.148 sim s`。未见本次规划拒绝由健康或时效门触发。

## 构建与产物

`bash tools/project.sh build ros` 完成 17/17 ROS 包，耗时 28.1 秒；`ego_planner` 只有既有弃用接口与未使用参数编译警告。运行目录为 `artifacts/runs/n10-20261026-340-spline-dynamics-diagnostics/`，逐次输出在 `vio.log`；源码补丁及哈希见 [0050 README](../../dependencies/patches/ego/README.md) 和结构化报告。
