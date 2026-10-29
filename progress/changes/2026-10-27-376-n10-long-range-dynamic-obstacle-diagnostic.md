# N10.3/#376 long-range dynamic-obstacle diagnostic

对话摘要：[2026-10-27-376](../../collaboration/dialogues/2026-10-27-376-n10-live-obstacle-diagnostic.md)

## 改动

- 修复 #376 run-local prelaunch 身份记录并绑定其 SHA；将实际 planner 路径、spawn 来源/hash/pose 与冻结协议比对后继续同一未解锁 SITL 栈。
- 完成单程 16 m PX4/EGO 目标、3 s 位置/yaw 真值到达评估、600 仿真秒 ACTIVE 保持、动态方箱观察、接触/净空和 PX4 末态读回。
- 新增 run-local B-spline/方箱净距离线回放 `artifacts/runs/n10-20261027-376-gatefree-cylinder0-observation/replay_n10_trajectory_box_clearance.py`，并生成 `n10-trajectory-box-clearance-replay.json` 和 `n10-arrival-metrics.json`。
- 新增 [轻量证据报告](../evidence/n10-live-obstacle-cylinder-correct-spawn-20261027-376.md) 及 JSON。未改产品源码、参数或验收阈值。

## 验证

- launch manifest 加载 `config/components/mapping/n10_horizon5_speed080_calibration.json`；spawn 为 `config/components/simulation/n10_long_range_spawn_minus8.json`、`[-8,0,0.3,0,0,0]`；runtime source/install 指纹 `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`。
- Flight `PASS`；action `position_yaw_tolerance_held`；独立达标驻留 3.114 s；post-goal ACTIVE hold 600.0 仿真秒，起止漂移 0.0233 m。
- Gazebo 确认动态方箱创建；新样条 #27 在注入 +0.552 仿真秒时首次得到 1.012 m 采样中心线净距；动态方箱采样机体净空 0.830 m，扣采样运动余量后 0.813 m。总场景限制净空为 0.1249 m，调整后 0.1076 m；违规接触 0。
- `evaluate_n10_arrival.py`：诊断检查通过，最长联合位置/yaw窗口 245.3 sim s / 276.5 wall s，最大位置误差 0.299953 m、最大 yaw 7.193°；窗口覆盖目标后保持，不能替代 N10.4 的正式任务反馈窗口定义。
- 独立 PX4/桥接末态读回为 LANDED、disarmed、control disabled、zero control；`bash tools/project.sh stop n10-20261027-376-gatefree-cylinder0-observation` 后容器退出码 0。

## 局限与下一步

该运行只贡献 N10.3 校准数据，不关闭 N10.3。位置误差 margin、跟踪误差语义、样本重复性、制动、时效时间域及故障退出边界仍待处理。#377 使用同一 planner/spawn，按本次水平速度观测选择 `[0.70,0.80] m/s` caller-cancel 制动触发窗；它是采样条件，不是速度限制。
