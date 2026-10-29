# #337 N10.3 16 m 长航程校准：安全失败

结论：**未通过；记录为安全失败，不计入 N11–N16。** 飞机完成预检和垂直起飞后，16 m goal 被 EGO 拒绝；没有执行水平目标航段，也没有开始 600 仿真秒保持。

## 结果

- PX4 只读预检通过，RTF `0.906`；official_ego 起飞准入通过。
- action 已发送，目标为 `[15.983792234034937, -0.006343994411606397, 1.0226580697495233]`（ENU）、yaw 偏移 `0.200 rad`、驻留 3 仿真秒。EGO 在约 `0.08` 仿真秒返回 `planner_full_curve_planning_failed`。
- EGO 日志显示 path optimization success，但最终样条在既有 3 次有界时间重分配后仍未证明速度／加速度可行，未发布 READY trajectory。飞机没有水平朝目标移动；离目标真值最小误差仍约 `16.000 m`。
- 健康未误锁：PRESTREAM 到 LANDED 共 `28.624` 仿真秒、真值配对路径 `1.880 m`（垂直起降），raw VIO 最大位置误差 `0.0117 m`，最大 yaw 误差 `0.0436°`，无 invalid localization。此短窗口不支持 16 m 或 600 秒结论。
- 真值接触判断通过、无违规接触；终态 PX4 `arming_state=1`，bridge `LANDED`、disarmed。live out-of-map 拒绝读回通过，随后已停止本项目容器。

## 根因边界

活动参数是 `max_vel=0.10 m/s`、`max_acc=0.25 m/s²`、`planning_horizon=5 m`。目前证据将问题定位在最终样条的动力学可行性门，不是定位健康或地图身份；但不能把根因单独归到“16 m 太远”，因为 EGO 本次规划的是约 5 m 局部目标，而且目标速度／路径状态也会影响样条。

下一轮 #338 固定 16 m 目标和其余输入，只把 planning horizon 5 m 改到 2 m，检查更短局部曲线是否通过同一动力学门。具体样本、哈希和读回见[JSON 报告](n10-long-range-calibration-20261026-337.json)，完整运行数据在 `artifacts/runs/n10-20261026-337-long-range-vio/`。
