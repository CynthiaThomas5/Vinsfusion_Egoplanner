# P5 零偏移 PX4 yaw 对齐复测 #218

对话摘要：[2026-10-20-012](../../collaboration/dialogues/2026-10-20-012-p5-anisotropy-yaw-alignment-repeat.md)。轻量报告：[run #218](../evidence/p5-vins-anisotropy-filter-yaw-alignment-repeat-20261020-218.json)。

## 结果

- 使用哈希确认的#207零偏移目标和run-local `0008=0.01`。前置条件通过，导航action得到`position_yaw_tolerance_held`成功结果。
- action成功后bridge因`operator_disable`进入LANDING，随后记录`px4_frame_alignment_drift`。在fault reason持续报告时的一组新鲜配对中，yaw error为0.196549 rad，高于0.15 rad门限；平移误差为0.019262 m，低于0.15 m门限；pair age/gap为0.101/0.096 s。这直接表明该fault窗口内yaw分支越限。
- 最早显示fault reason的bridge detail中yaw已回落为0.105805 rad。诊断流的采样节奏没有捕获精确锁存时刻，因此证据支持yaw门解释，但不标记具体触发时刻。
- accel-bias峰值0.107273 m/s²，没有触发0.15 m/s²门。action成功后定位在LANDING期间以normalized_cost=1.018525失效。
- flight harness没有观察到bridge `LANDED`，将整轮标为FAIL。PX4 ULog确认触地和最终解除武装，无dropout，观察到EV融合、GNSS aiding零；触地后短暂DESCEND/failsafe。
- 尝试的run-local `/sensors/d435i/imu` observer启动，但SIGINT期间rclpy默认handler关闭context，导致清理阶段抛出`ExternalShutdownException`并且没有生成IMU trace。该轮没有提供IMU样本证据。

## 验证

- run-local colcon build：6 packages finished；见`artifacts/runs/p5-px4-vio-ego-anisotropy-filter-imu-trace-20261020-218/colcon-build.log`。
- 新增的run-local IMU recorder、flight harness通过`py_compile`，两个shell wrapper通过`bash -n`；运行时SIGINT收尾错误已记入报告。
- `analyze_px4_ulog.py`按#218 run id修正后运行完成，生成hash索引中的`landing-failsafe-timeline.json`。
- 轻量报告对run配置、flight report、PX4 ULog、alignment detail、观测器日志和源码记录作SHA-256索引。

## 局限与下一步

该run不是P5验收，action成功也不能抵销LANDING期间的定位和对齐保护。yaw detail证明同一fault窗口中yaw超过门限，但首次锁存时刻未直接采到。下一轮修复run-local采集器的信号处理顺序，再捕获原始IMU输入与VINS遥测；不订阅真值、不改变门限和控制。P5和GOAL A–H继续进行。
