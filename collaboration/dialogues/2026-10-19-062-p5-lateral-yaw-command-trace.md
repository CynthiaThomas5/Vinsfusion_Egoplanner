# P5 横移／偏航目标诊断与 EGO→PX4 命令链追踪

## 任务摘要

继续推进 `GOAL.md`，在不改变定位质量门的前提下测试横移和 yaw 目标，并保存 EGO 航向命令与 PX4 实际设定点，以定位终端 yaw 未到达发生在哪个运行阶段。

## 用户与项目约束

- 仅运行单 D435i SITL，不进行真实设备飞行。
- 真值只给独立只读诊断 observer；VINS、建图、导航和 PX4 bridge 不订阅真值。
- 保持 `max_normalized_cost=1.0`、VIO PX4 future 容差0.065 s和 PX4 bridge 唯一控制发布者。
- 失败及中止运行保留为诊断证据，不据此标记 P5 或 GOAL 条款通过。

## 结果与决定

- #177/#178 都用 run-local 目标请求 ENU 横移0.5 m及 yaw +45°。两轮前置门通过；首次 `normalized_cost_exceeded` 分别在派发目标后1.373秒和0.769秒，之后 action 中止并安全降落解除武装，末态 `failsafe=false`。
- #177 只得到约0.048 m的真值横移；flight-window 真值 yaw 范围0至−21.24°。#177 有271组配对位姿，位置 RMSE/P95/最大0.1815/0.4999/0.5351 m；normalized_cost/误差 r=0.725，long-track/误差 r=+0.465，后者与前两轮相反。
- #178 在 run-local probe 里记录匹配目标的完整 `PositionCommand` yaw/位置及 PX4 `TrajectorySetpoint` yaw/位置/时间戳。75条 READY command 的早期航向为−0.289至−0.216 rad，与终端目标 +0.785 rad相差至少1.000 rad；该轨迹仍在起点附近，健康门在终端 yaw 段到达前已取消。PX4 yaw setpoint 与变换后的早期 command 具有约0.041 rad近常量偏差；该值可能包含 frame yaw alignment，不能据此判断转换有缺陷。
- #178 的 287组 flight-window 位姿位置 RMSE/P95/最大为0.1367/0.3942/0.4165 m；normalized_cost/误差 r=0.624，long-track/误差 r≈0。#175–#178 多轮 short-run 中 cost 与 bias 的正相关有重复方向，long-track 相关方向不稳定；不能据此作因果或冻结验收阈值。
- 静态与接口测试显示 ENU/NED yaw conversion、导航 action 到 EGO target 复制、traj_server yaw spline 均通过。由于任务在轨迹终端航向到达前被定位质量门中止，尚未验证目标 yaw 的端到端跟踪，也未发现已证实的坐标缺陷。

## 待办

分析 quality telemetry、传感器输入与运动起始的时间线，理解目标派发后质量代价为何迅速越限；保持 fail-closed，直到有独立证据支持任何门限变更。再验证完整 EGO yaw spline 到 PX4 与真值 yaw 的跟踪。无真值重复任务、障碍净空、地图快照、故障与长时验收仍未完成。
