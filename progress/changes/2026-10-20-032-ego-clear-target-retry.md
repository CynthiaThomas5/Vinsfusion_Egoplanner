# GOAL B/C EGO 开阔短目标重试 #258

关联对话：[2026-10-20-032](../../collaboration/dialogues/2026-10-20-032-ego-clear-target-retry.md)。

启动 mapper、EGO、深度健康门与定位适配器；取消独立地图点云采样器。目标探针要求TRACKING定位、`MapStatus.input_ready`、至少500占据点、点云非空并连续0.5秒，才向当前epoch的 `odom` frame发出一个(0.7,0.0,1.0) m目标。保持健康策略原样，EGO膨胀／地面下界仅run-local为0.5/−0.05 m。

本轮在目标探针窗口内以 `imu_stale` 失效；地图reset，最后MapStatus `input_ready=false`、占据0，转发204帧深度、7个关键帧。探针40秒结束为 `timeout_before_ready`，没有goal或B-spline。raw VINS 65秒仍产生634条优化、8,359条传播、644条telemetry；传播输出源戳最大间隔135 ms、墙钟接收间隔332.5 ms。输出流不等同适配器直接IMU输入，不能归因根因。#255在相关配置下曾维持TRACKING至后续normalized-cost失效，因此本轮与历史结果也表明运行有波动。

没有控制器、PX4、轨迹执行、setpoint或真值订阅。无目标结果属于健康前置失败，不证明规划或避障能力。保持GOAL B/C/D/F与阶段状态不变。详细数值和哈希见[证据报告](../evidence/p2-ego-clear-target-retry-20261020-258.json)。

验证：容器退出0；`gz sdf -k`报告 `Valid`（保留 `gz_frame_id` schema warnings）；40秒goal探针与65秒raw VINS捕获完成；容器清理后无活动测试容器。项目源码、配置和健康阈值未改变，不运行colcon构建。

下一步保持0.5 m全栈配置，直接采集双目与IMU源龄／接收节奏，并保留健康与地图前置门。只有稳定TRACKING且MapStatus ready、占据非空后才发一个短目标；不启动轨迹执行或PX4。
