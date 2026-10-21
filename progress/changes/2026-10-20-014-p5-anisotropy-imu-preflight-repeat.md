# P5 run-local anisotropy filter 横移前置门复测 #220

对话摘要：[2026-10-20-014](../../collaboration/dialogues/2026-10-20-014-p5-anisotropy-imu-preflight-repeat.md)。轻量报告：[run #220](../evidence/p5-vins-anisotropy-filter-imu-horizontal-preflight-repeat-20261020-220.json)。

- #220 复用#219的横移0.30 m/+30°配置、0.01 filter和只读IMU observer，ROS domain 231与Gazebo partition独立。目标配置SHA与#192相同。
- 六包 colcon build通过；shell wrapper语法与run-local Python脚本编译预检通过。harness result=FAIL，action_goal_sent=false；定位稳定窗与PX4遥测稳定窗均未通过。bridge保持DISABLED，vehicle保持landed/disarmed，无控制目标。
- 定位最后valid状态source stamp=12.404 s；首个invalid在12.648 s，reason=optimized_stale，good_pairs=68、accepted_optimized=59。VINS telemetry随后继续到48.316 s，末样报告initialized、solve_current、solver_usable=true，normalized_cost=0.028203、long_tracks=36。
- IMU observer保留12,213个source-stamped样本，200 Hz、最大gap8 ms、零stamp回退、全数值有限，且shutdown graph仍发现d435i_sensor_bridge为publisher。ULog无dropout，GNSS flags为零，EV position/yaw/velocity各7/76样本为true；无Offboard/解锁、最终仍landed/disarmed。
- 图片observer在source stack关闭时由ExternalShutdownException退出，未生成quality image manifest；本轮无目标或cost越线。它没有影响harness的preflight结果。
- 验证：python3 artifacts/runs/p5-px4-vio-ego-anisotropy-filter-imu-horizontal-20261020-220/analyze_px4_ulog.py成功生成landing-failsafe-timeline.json；run report中36项SHA索引核对通过。未改canonical源码、健康门限、PX4参数或控制逻辑。
- 局限与下一步：当前报告无法判定原始VINS odometry是否停止，还是适配器失去有效配对。下一轮加只读raw /vins_raw/<epoch>/odometry capture，与telemetry/IMU按source stamp对齐；新domain/partition，保持profile和阈值。P5未通过。
