# P5 零偏移 PX4 yaw 对齐复测 #218

- 日期与任务 ID：2026-10-20，继续项目 Goal；在#217之后复测零偏移对齐故障，并尝试run-local IMU只读采集#218。
- 用户约束：只推进单D435i仿真导航；不把run-local `0008`并入canonical VINS；PX4 bridge独占控制；最终组合不输入真值；不得降低bias、quality、freshness或PX4对齐门限。
- 已确认运行：ROS domain229、独立Gazebo partition、经#207 SHA确认的0平移/0 yaw目标，filter仍为0.01。前置条件通过，导航action成功并保持position/yaw tolerance。
- 对齐结果：成功action后bridge由`operator_disable`进入LANDING。detail随后报`px4_frame_alignment_drift`；在一组新鲜配对中，yaw error=0.196549 rad（门限0.15），position drift=0.019262 m（门限0.15），pair age/gap=0.101/0.096 s。这直接显示yaw门在已报告fault的窗口内越限；第一条记录fault reason时yaw已回落至0.105805 rad，因此精确锁存时刻没有捕获。
- 定位/PX4：accel-bias峰值0.107273 m/s²，未越0.15门；action成功后定位另因normalized_cost=1.018525失效。flight harness最终因未观察到bridge `LANDED`将整轮报告为FAIL；PX4 ULog确认AUTO_LAND、触地、最终disarmed，且无dropout、有EV融合、GNSS aiding零，触地后短暂DESCEND/failsafe。
- IMU observer：启动并创建了`/sensors/d435i/imu`订阅，但SIGINT期间rclpy context先关闭，随后observer在查询publisher信息时崩溃；没有写入`imu-trace.json`。不把这轮计作原始IMU采集证据。
- 结论：#218支持#216的yaw对齐门解释，但锁存瞬间仍待更密集事件记录。P5未通过。
- 相关证据：[轻量报告](../../progress/evidence/p5-vins-anisotropy-filter-yaw-alignment-repeat-20261020-218.json)、[改动记录](../../progress/changes/2026-10-20-012-p5-anisotropy-yaw-alignment-repeat.md)。
- 下一步：修正run-local采集器信号关闭顺序并在另一轮仿真验证；不改健康门、控制或真值输入。
