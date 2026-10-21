# GOAL B/C EGO 全栈输入新鲜度与短目标诊断 #259

关联对话：[2026-10-20-033](../../collaboration/dialogues/2026-10-20-033-ego-input-freshness-load-diagnostic.md)。

在0.5 m run-local膨胀、全mapper/EGO负载和原健康阈值下，增加独立双目／IMU源龄观察器。目标探针保持健康、MapStatus ready、至少500个占据点、非空原／膨胀点云、稳定0.5秒及EGO订阅者等前置门；满足后仅发送一次(0.7, 0.0, 1.0) m目标。

观察器收到左右图各1,152帧，3 ms内配对1,151组，最大接收源龄110/129 ms；IMU收到7,066条，最大源龄31 ms。观察窗55.066秒内定位保持TRACKING，没有`left_stale`或`imu_stale`。目标发送时map有915个占据点，探针收到匹配epoch的三阶B-spline，共10个位置控制点。没有controller、PX4或轨迹执行。

EGO仍有98条`odom or depth lost!`日志，位于三个仿真时间簇（8.977–9.241、30.642–30.958、50.696–54.646秒），数量分别8、10、80；日志显示last_sync_in_map=1。运行观测到一次`refine_success=1`和一次进入`EXEC_TRAJ`日志，没有终点障碍警告或`EMERGENCY_STOP`。这些结果显示全栈EGO更新间隔仍存在；源龄观察器不能证明适配器逐样本接收，也没有逐条跟踪adapter发布到EGO take，因此不能确定根因。

证据报告：[p2-ego-input-freshness-load-diagnostic-20261020-259.json](../evidence/p2-ego-input-freshness-load-diagnostic-20261020-259.json)。原始运行目录：`artifacts/runs/p2-ego-input-freshness-load-diagnostic-20261020-259`。

验证：运行容器退出0；`gz sdf -k`报告Valid（保留已有`gz_frame_id` schema warnings）；2个shell脚本通过`bash -n`、4个Python脚本通过编译检查；运行后`docker ps`为空。项目源码、配置与健康阈值未修改，不运行colcon构建。结构检查、证据哈希与差异检查待本记录完成后统一执行。

后续#260在独立raw VINS订阅仍看到telemetry持续时，定位适配器以`telemetry_stale`锁定并使地图reset，未进入EGO输入诊断窗口。#261–#266已完成run-local定位telemetry回调观测及负载隔离；具体投递/调度原因仍未确定。下一步使用publisher-side低频MapStatus trace，并保持不接轨迹控制或PX4。
