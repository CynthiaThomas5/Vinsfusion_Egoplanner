# #339 N10.3 horizon 2 m PX4 校准：最终样条仍被安全拒绝

结论：**该参数对照未通过，失败保留。** 将 EGO planning horizon 从 5 m 改为 2 m 没有解除 #337 的最终样条动力学可行性拒绝；没有水平目标运动或长时保持证据。

## 运行结果

- 新冷启动预检与 official_ego 起飞准入通过。入口确认 `/navigation/ego_goal` 图中恰好有一个 `uav_navigation` publisher 和一个 `drone_0_ego_planner_node` subscriber；planner 实际加载 horizon `2.0 m`、逐轴 `max_vel=0.10 m/s`、`max_acc=0.25 m/s²`。
- 原 16 m 单程目标已发送，目标包含 `+0.1 m` 高度、`+0.2 rad` yaw，native dwell 为 3 仿真秒。EGO 在 `0.056` 仿真秒／`0.0775` 墙钟秒后返回 `planner_full_curve_planning_failed`。没有 READY trajectory，goal 最小真值距离为 `16.00199 m`，dwell 未开始，600 仿真秒 ACTIVE hold 未开始。
- 接触评估通过：无违规接触，并观察到落地接触；live out-of-map 拒绝探针通过。PX4 `arming_state=1`，bridge 最终 `LANDED`、`armed=false`、`landed=true`。本次项目容器已停止；没有触碰其他容器。
- 固定 SE(3)、不拟合尺度的只读 raw VIO 评估覆盖 PRESTREAM 到 LANDED `28.344` 仿真秒和 `1.8982 m` 路径（起飞／落地），位置误差 max `0.00789 m`、yaw 误差 max `0.05263°`，430 对齐样本、truth 支持率 `0.9979`、无 invalid localization。此窗口不构成长航程或 600 秒稳定性证据。
- 仿真时钟无回退；`/clock` 最大正间隔 `0.096 s`，最大墙钟回执间隔 `0.122 s`。定位状态最大间隔 `0.133 sim s`，墙钟回执间隔 `0.151 s`。健康与时效门均未拒绝本任务。

## 结论边界与下一步

Horizon 5→2 m 的唯一规划变量没有通过同一个最终 spline dynamics gate，故 #338/#339 假设被否定。证据把失败定位在 EGO 最终 B 样条速度／加速度可行性门，但现有日志没有记录哪个分量超限及超限比例。现阶段不能判断是速度、加速度、某轴分量或两者共同主导，也不能据此改速度值或加速度界。

下一步先给现有检查增加只读数值诊断：记录每次 refine 后的逐轴最大速度／加速度、当前允许值、容差与归一化 ratio；保持算法、阈值、任务和参数不变，再用 #340 单次 PX4/SITL 诊断复现该拒绝。只有测到超限项，才决定是否需要新的单变量参数校准。N10.3 未通过。

运行目录：`artifacts/runs/n10-20261026-339-horizon2-16m/`。主要证据的 SHA-256 见[结构化报告](n10-horizon2-calibration-20261026-339.json)；运行级输入清单在 `n09-run-manifest.json`。
