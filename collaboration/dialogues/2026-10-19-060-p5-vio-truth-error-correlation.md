# P5 VIO 质量与只读真值轨迹关联诊断

## 任务摘要

继续完成 `GOAL.md`。#171 的 canonical VIO/EGO SITL 在前置门和目标派发后因定位 `normalized_cost` 超限而 fail-closed，必须保持 1.0 质量门，不凭单次运行放宽。

## 用户与项目约束

- 只推进单 D435i 仿真项目，不启动真机飞行。
- 在线真值输入只用于隔离的诊断/`debug_truth` 用途；最终 VIO 组合不得让定位、建图、规划或 PX4 bridge 订阅真值。
- PX4 Offboard 控制出口仍由 `uav_px4_bridge` 独占。
- 保留所有失败 run；P5 或 GOAL A–H 只有满足实际验收证据后才能标为通过。

## 决定与结果

- 扩展 `tools/probe_vins.py`，仅在用户/运行脚本显式传入 `/debug_truth/base_odometry` 与 `/sensors/d435i/imu` 时，采集只读诊断真值和 IMU；默认模式仍不订阅真值。
- 新增 `tools/evaluate_vio_quality_alignment.py`，以首次配对位姿进行一次固定 SE(3) 对齐，不拟合尺度、不分段对齐，并按源时间戳关联 VINS quality telemetry 与位置误差。
- #172/#173 因 lazy bridge 的早期 topic discovery 检查退出；#174 的运行探针文件遗漏，均在发 goal 前排除。
- #175 启动完整 `vio_closed_loop` 组合并单独增加只读真值 observer。ROS graph 显示 raw truth topic 的唯一 subscriber 为 `raw_vins_readonly_probe`；PX4 bridge graph 没有真值订阅。目标因 `normalized_cost=1.1460447` 失败，PX4 降落并解除武装，末态 `failsafe=false`。
- #175 的 269 组 flight-window 位姿一次固定 SE(3) 对齐后，位置 RMSE/P95/最大为 0.3758/1.0532/1.3578 m，姿态 RMSE 为 0.3695°。normalized_cost 与位置误差 Pearson r=0.560；long-track 数量 r=−0.813，accel/gyro bias 范数 r=0.788/0.846，原始输入特征数 r=−0.024。首次 health gate 的匹配质量遥测 stamp 为 35.412 s、位置误差约 0.0110 m，约 2.51 仿真秒后误差超过 0.30 m。单轮数据只能说明时序关联，不能建立通用质量阈值。
- `max_normalized_cost=1.0` 与 VIO future 容差 0.065 s 均未改变；后者仍为 PROVISIONAL。

## 待决与下一步

重复诊断并增加不同运动段，确认特征持续率、重投影残差、VINS bias 和只读真值误差之间的关系；保持导航控制栈无真值订阅。随后继续 P4 轨迹跟踪/到达/绕障、无真值重复任务、地图快照、故障注入及十分钟运行。P5、P6 和 GOAL A–H 均未完成。
