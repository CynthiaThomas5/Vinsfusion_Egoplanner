# P5 run-local anisotropy filter 横移与 IMU 直接输入复测 #219

对话摘要：[2026-10-20-013](../../collaboration/dialogues/2026-10-20-013-p5-anisotropy-imu-horizontal-repeat.md)。轻量报告：[run #219](../evidence/p5-vins-anisotropy-filter-imu-horizontal-repeat-20261020-219.json)。

- #219 使用 #192 的 0.30 m 横移、+30° yaw 配置及 0008=0.01 run-local 过滤器。修复后的只读观察器在 /sensors/d435i/imu 捕获12,619条样本，约200 Hz，stamp 单调且最大间隔8 ms；启动时 ROS graph 显示唯一发布者 d435i_sensor_bridge。
- 六包构建完成。导航 action 以 position_yaw_tolerance_held 成功，run harness记录PASS、LANDED/disarmed。估计 accel bias 峰值0.133932 m/s²，未达到0.15 m/s²门限。
- action 后bridge进入LANDING；VINS在source stamp 31.188 s首次 normalized_cost=1.026064，31.252 s定位以 normalized_cost_exceeded 无效。31.088 s IMU出现143.72 m/s²加速度范数峰值；PX4 sensor_combined 同刻也记录冲击。PX4本地位置随后从距底约0.106 m下降至0.027 m并减速；这与着陆冲击时间相符，但不能据此断言代价根因。
- 越线帧757个视觉 residual blocks全部和12组双目图匹配；最大图像时间差与stereo skew均为0。大于1.5 px的残差远离拟合图像强边缘，未重复先前 edge-aligned pattern。视觉、IMU时间相关性均为单轮诊断，不是因果证明。
- ULog重算：dropouts=0，EV position/yaw/velocity融合标志均观察到，GNSS aiding flags全零，AUTO_LAND、touchdown、最终disarm；无failsafe或电池故障标志。P5仍未通过。
- 验证：运行目录中六包 colcon build 通过；capture/harness Python 编译及两个 shell wrapper 语法预检通过；python3 analyze_px4_ulog.py 成功；analyze_all_feature_residuals.py 与 analyze_image_edge_correlation.py 重算视觉残差，Huber重算差约5.7e-13；报告所列781张图像SHA全部匹配。
- 局限与下一步：单次横移不满足每场景三次、绕障净空及零碰撞要求；没有#218的直接D435i IMU轨迹作同源对照。用新domain/partition重复同一目标与观察器，不改阈值或健康门。
