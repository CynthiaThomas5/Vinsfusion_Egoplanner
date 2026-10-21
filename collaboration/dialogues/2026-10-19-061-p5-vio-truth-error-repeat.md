# P5 VIO 质量与只读真值轨迹关联独立复测

## 任务摘要

继续推进 `GOAL.md`，对 #175 的质量遥测—真值误差关联做一次独立冷启动复测。保持 `max_normalized_cost=1.0` 和 VIO PX4 future 容差 0.065 s；不进行实机飞行。

## 约束与决定

- 只读真值仅用于诊断 observer。导航、建图、定位和 PX4 bridge 不得订阅 `/debug_truth/base_odometry`。
- `uav_px4_bridge` 保持唯一 PX4 控制设定点发布者；失败目标必须保留 fail-closed 和安全降落结果。
- 不根据两次短时相关性放宽质量门或宣称因果。

## 结果

- #176 修复 run-local 检查时序：等待 truth topic 确认恰有一个 `ros_gz_bridge` 发布者和一个 `raw_vins_readonly_probe` 订阅者后，才运行导航探测。活动图检查与 bridge node info 显示 PX4 bridge 无真值订阅。
- canonical `vio_closed_loop` goal 通过前置和稳定门后派发，随后以 `localization_normalized_cost_exceeded` 中止。PX4 降落并解除武装，末态 `failsafe=false`。
- 90秒采集得到3,046条真值、12,017条 IMU、910条优化 VIO。279组 flight-window 位姿经单次固定 SE(3) 对齐（尺度固定为1）后，位置 RMSE/P95/最大为0.314/0.883/1.164 m，姿态 RMSE为0.315°。
- normalized_cost、long-track 数、加速度 bias 范数、陀螺 bias 范数与位置误差的 Pearson r 分别为0.714、−0.750、0.554、0.771。首个健康门遥测代价1.196时对齐误差约0.018 m；约2.532仿真秒后位置误差超过0.30 m。
- #175/#176 两轮的门控先于明显误差增长，long-track 关联为负、bias 关联为正；这是短时序关联重复，不证明因果、通用阈值或最终精度。

## 待办

用原质量门测试明确的横移或偏航运动段，并继续保留只读真值隔离。无真值重复导航、障碍净空、地图快照、故障注入、长时测试和 P4/P6 仍待验收。
