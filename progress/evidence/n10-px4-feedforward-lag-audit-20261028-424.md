# N10.3/#424 PX4 位置跟踪滞后与前馈实现审计

## 问题与方法

#393 已把 EGO 命令位置误差逐点与实际全机障碍净空关联，但大跟踪误差的原因未区分。本项检查 PX4 自身的 `TrajectorySetpoint.position` 与 `VehicleLocalPosition`，两者均在 PX4 本地 NED 参考系，不依赖 VIO 到 Gazebo 的 SE(3) 对齐。

初始 0–3 s、20 ms 步长扫描在不同 lag 使用了不同样本数，不能直接比较。修订后的离线评估器另做固定对照：在同一批本地位置样本上，对比当前设定点与 `t−1.06 s` 的设定点，要求两种查询均由不超过 40 ms 的实际设定点括区支持，不外推。1.06 s 是 #381/#385 先前变支持扫描选出的候选；这个 matched-support 复算使用相同归档，不是独立盲测。三个 epoch 分开统计，不合并。

## 同样本对照

| 运行 | 同样本数 | 0 s 回看误差 RMS / P95 | 固定 1.06 s 回看误差 RMS / P95 | 0–3 s 全网格共同样本 |
| --- | ---: | ---: | ---: | ---: |
| #381 | 1,645 | 0.534 / 0.621 m | 0.037 / 0.054 m | 0 |
| #385 | 1,025 | 0.511 / 0.629 m | 0.034 / 0.066 m | 0 |
| #412 | 444 | 0.275 / 0.324 m | 0.028 / 0.070 m | 0 |

固定对照在三次运行里都显示明显的时间平移相关性；它表明当前机体位置更接近约一秒前的 PX4 位置设定点。它**不能证明**实际控制延迟正好为 1.06 s，也不能归因于单一实现原因。#412 在 40 ms 括区限制下共同样本只有 444 个，结论仍为诊断线索。

初始变支持扫描分别给出 #381/#385 的最小 RMS 候选 1.06 s、#412 为 1.08 s，但样本数量随 lag 改变。固定对照只用于排除该样本数变化的混杂；0–3 s 全候选共同覆盖为零，不能报告一个有全面支持的连续 lag 曲线。

## 源码路径证据与待验证修复

- EGO `traj_server.cpp` 在轨迹时刻 `t_cur` 发布 `PositionCommand.position=traj(t_cur)` 并附当前 source stamp；该位置本身没有 1 s 的未来偏移。
- 桥接器将 `/position_cmd` 转换成 `NEDTrajectorySetpoint`，其中已计算 NED position、velocity 和 acceleration；但 `_position_for_output()` 只缓存并返回 position/yaw。`_publish_control()` 随后发布 finite position，velocity、acceleration 和 yawspeed 全部为 NaN。
- 当前 PX4 `PositionControl::_positionControl()` 把 finite velocity setpoint 与位置 P 项相加作为速度输入；本地 `offboard.md` 也明确允许 position setpoint 携带非 NaN velocity/acceleration feed-forward。PX4 仓库 revision 为 `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`。
- 这使“桥接器丢弃 EGO 的速度前馈，导致机体追赶移动位置 setpoint”成为**值得做因果验证的修复假设**，不是已证明根因。时间映射、消息采样、PX4 控制和动力学仍可能贡献该相关性。

建议当前 #415 安全收尾后，先做一个受控实现对照：保持位置、航迹、速度／碰撞行为、参数和评估方法不变，只把已经转换到 NED/机体参考点的 EGO velocity feed-forward 传到 PX4 `TrajectorySetpoint.velocity`；初始对照仍将 acceleration 保持 NaN，避免把未做 lever-arm 二阶导数修正的加速度也混入变量。先补转换与发布单测，再做 ROS/PX4 构建和一次代表性 SITL，比较同样本跟踪误差、1.06 s 相关性、4 ms 实际净空和接触记录。不得通过删改跟踪门限掩盖结果。该修改在 #415 活动期间**没有实施**。

## 产物与限制

- 修订 evaluator：`tools/debug_truth/evaluate_n10_px4_tracking_lag.py`；两个合成数据单测通过。
- 每次归档的独立结果：`artifacts/runs/n10-20261027-381-vins-velocity-full-route/n10-px4-position-tracking-lag-n10audit-v3.json`、`artifacts/runs/n10-20261027-385-arrival-dwell4-retry/n10-px4-position-tracking-lag-n10audit-v3.json`、`artifacts/runs/n10-20261028-412-speed040-yaw-lookahead-calibration/n10-px4-position-tracking-lag-n10audit-v3.json`。
- 本项未更改运行源码、配置或验收阈值；未构建、未启动 SITL，不能关闭 N10.3 或 N10.4。
- #415 当前 PX4 尚未达到 landed/disarmed/control-disabled/zero-control；在该运行安全结束前不改运行源码、不开始 N10.5。
