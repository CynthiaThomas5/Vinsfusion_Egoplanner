# #341 N10.3 refine ratio 哨兵修正：任务仍被 X 轴速度门拒绝

结论：**ratio 哨兵修正已生效，但没有解决 16 m 长程初始曲线拒绝。** 对未超限的加速度项现在贡献 0；最终速度／加速度门和容差原样保留。EGO 仍不能提供 READY 曲线，未发生水平目标运动。

## 构建与运行

- `bash tools/project.sh build ros`：17/17 ROS 包完成，15.7 秒；完整日志 `artifacts/runs/n10-20261026-341-spline-reallocation-ratio/build-ros.log`。
- fresh 单 D435i official_ego PX4/SITL；planner 实际加载 horizon `2.0 m`、`max_vel=0.10 m/s/axis`、`max_acc=0.25 m/s²/axis`、tolerance `0.05`。Preflight 与起飞准入通过。
- 16 m goal 已发送，EGO 以 `planner_full_curve_planning_failed` 中止；累计 10 次最终规划拒绝、40 条逐轴汇总检查。每次最终序列 ratio 为 `2.8013 → 2.6460 → 2.8710 → 3.0551`；ratio 数据显示无加速度越限时 `acceleration_ratio=0`，修正生效。
- 最大 B 样条速度导数控制点为 `vx=0.305505`、`vy=0.001847`、`vz=0.104571 m/s`，超过含容差门 `0.1051 m/s`；最大加速度导数控制点 `0.061277 m/s²`，低于含容差门 `0.2626 m/s²`。这里是 B 样条导数控制多边形的上界，不是 PX4 实际飞行速度。SITL 没有水平目标运动、READY 轨迹、goal dwell 或 600 sim-s hold。
- #341 的初始 X 速度 `0.280132 m/s` 与 #340 初始 `0.190426 m/s` 不同；同一 runner/配置下跨 fresh run 的初始 spline 有变化，支持用逐次实测判定，不由配置字段推断实际值。#341 的最大 X 控制点速度仍比 #340 高，故“只修正 ratio 哨兵即可清除拒绝”假设被否定。

## 独立评估与末态

- 固定单次 SE(3)、scale=1 的 raw VIO 评估覆盖 PRESTREAM→LANDED `28.676` 仿真秒、`1.8939 m` 起降路径：位置误差 max `0.01161 m`、yaw max `0.04246°`，434 对样本、invalid localization `0`；不代表 16 m 误差或长时漂移。
- `/clock` 无回退、最大源间隔 `0.100 s`；localization status 最大源间隔 `0.144 sim s`。Contact 评估通过、违规接触 `0`、landed contact 已见；live terminal refusal 通过。
- PX4 `arming_state=1`，bridge `LANDED`、disarmed；`bash tools/project.sh stop n10-20261026-341-spline-reallocation-ratio` 返回 0，容器 `exited 0`。无其他容器被触碰。

## 结论和后续

#340 已识别 X 轴速度门是失败项；#341 修正了 ratio 计算，却未让低速 horizon2 长程目标达到原门限。当前证据不支持把 0.10 m/s 参数当作该 16 m 任务可执行，也不支持直接提高速度后宣称安全。下一步先核对 EGO local-target/end-derivative 与时间重分配后的控制点变化，并对候选速度配置补齐运行曲线和 N08 速度/制动证据，再决定是否有足够依据扩大支持范围。#341 的 patch 会影响旧版本以 2 次 refine 成功的 N09 运行；N10.6 在最终候选锁定后必须审查并重跑受影响出口。

结构化哈希见[JSON 报告](n10-spline-reallocation-ratio-20261026-341.json)，原始运行数据位于 `artifacts/runs/n10-20261026-341-spline-reallocation-ratio/`。
