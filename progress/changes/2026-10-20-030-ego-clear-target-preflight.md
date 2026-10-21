# GOAL B/C 开阔短目标前置门复测 #256

关联对话：[2026-10-20-030](../../collaboration/dialogues/2026-10-20-030-ego-clear-target-preflight.md)。

本轮在 #255 场景基础上只把 run-local 手动目标改为(0.7,0.0) m；保留0.5 m膨胀、−0.05 m下界及不启动控制器／PX4的约束。探针要求定位有效、MapStatus `input_ready`、至少500个占据点以及EGO goal订阅者就绪后才发goal。

定位状态在探针窗口以 `left_stale` 无效，planner probe 记录 `timeout_before_ready`，未发送目标、未收到B-spline。50秒映射探针收到872帧深度，但优化里程计转发、EGO深度／位姿配对、原占据和膨胀占据为0；MapStatus最后为 `input_ready=false`、`occupied_point_count=0`。原始VINS只读探针记录612条优化、8,085条传播、622条telemetry，truth样本0。当前证据只说明原始输出与适配器运行状态在该轮不一致，不定位根因；不比较目标规划表现。

没有发布goal／轨迹，没有PX4、控制器、trajectory server、setpoint或在线真值订阅。GOAL B/C/D仍pending，P2阶段状态不变。详见[排除证据](../evidence/p2-ego-clear-target-preflight-20261020-256.json)。

验证：容器退出码1，分类为健康前置门失败导致的排除轮；场景 `gz sdf -k` 通过并报告 `Valid`（保留 `gz_frame_id` schema warnings）；run-local `bash -n` 和5个Python脚本语法检查通过；无活动测试容器。收尾时 `python3 tools/project_status.py` 通过；相关7份证据JSON解析通过，来源与原始产物哈希431/431匹配，工作区与暂存区 `git diff --check` 通过。项目源码无变化，不重复colcon构建。

后续#257在低负载下直接观察到左右图像最大源间隔66 ms、最大接收时源龄181／192 ms，没有`left_stale`；定位约41秒后以`normalized_cost_exceeded`锁定。#258在mapper/EGO活动、移除额外地图采样器后仍以`imu_stale`在目标前失效，raw VINS输出继续；未直接测适配器IMU输入。下一步保持0.5 m配置直接观察双目和IMU接收节奏，再按健康与MapStatus门决定是否发目标。
