# #338 N10.3 局部规划时域单变量复核协议

状态：**采样前协议已冻结；尚无运行数据。** 运行 ID：`n10-20261026-338-horizon2-16m`。#337 的失败保持不变。

## 假设与变量

#337 在 path optimizer 成功后，最终 B 样条仍未通过速度／加速度可行性复核。EGO 源码用 `planning_horizon` 选择局部目标。本轮只改变一个变量：`planning_horizon_m` 从 5.0 m 降到 2.0 m；最大速度、加速度、地图膨胀、map-age、目标、相机、official_ego 和 PX4 桥都保持不变。假设较短的局部曲线能通过当前动力学门，并由 EGO 连续重规划抵达原 16 m 全局目标。

## 成功判据与保护

- 同一目标 `(16.0, 0.0, +0.1) m`、yaw `+0.2 rad`；原生 dwell 3 仿真秒，goal timeout 360 仿真秒。
- 到达需真值离线固定单一 SE(3)，position `<=0.30 m`、yaw `<=15°` 连续 `>=3.0 sim s`。不得用真值反馈给控制。
- 到达后才开始 600 仿真秒 ACTIVE hold。检查 localization、PX4 telemetry、sim clock 和桥状态；异常、15 秒仿真时钟停顿、watchdog 或接触问题时由唯一 PX4 桥降落。
- 与 #336 同一候选量：raw VIO max position `<=0.15 m`、max yaw `<=7.5°`，真实向量速度 `<=0.12 m/s`，tracking `<=0.15 m`，地图 source/occupancy age `<=0.4 sim s`，health receipt gates 保持 `0.5/0.3 wall s`。候选值需按结果和已有依据评审，尚未冻结。

实际到达和完整保持均未完成时，即保留为失败，不以参数值或规划器初始成功关闭。该诊断不证明障碍净空，也不计 N11–N16。详细哈希与保护条件见[结构化协议](n10-independent-calibration-protocol-20261026-338.json)。
