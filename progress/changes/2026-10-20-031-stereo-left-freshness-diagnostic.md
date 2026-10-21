# GOAL B/C 左右图像新鲜度隔离诊断 #257

关联对话：[2026-10-20-031](../../collaboration/dialogues/2026-10-20-031-stereo-left-freshness-diagnostic.md)。

新增 run-local 双目源龄观察器与仅按仿真时钟施加 Gazebo wrench 的无真值激励脚本。项目源码、配置、canonical launch 与健康阈值均未改变。本轮只运行传感器、VINS和定位适配器；不启动 EGO、mapping、目标、控制器或 PX4。

左右图像分别收到1,487／1,486帧，3 ms内双目配对1,485组；源戳间隔P50/P95/最大均为33/33/66 ms，接收时源龄最大181/192 ms，没有超过300 ms的间隔或源龄。定位约2.42秒进入TRACKING，持续有效至43.57秒，之后由既有 `normalized_cost_exceeded` 护栏锁定；没有出现 `left_stale`。raw VINS输出833条优化、10,990条传播、843条telemetry，数值有限，无解析错误。探针不订阅真值，run-local motion driver只订阅仿真时钟并按预定时间施力。

结合 #256 的363 ms telemetry源戳间隔与其锁定前389 ms优化输出接收间隔，图像新鲜度负载／调度是一个合理待查方向；#257的单独图像观察器不能证明适配器逐帧接收，且低负载运行未启动mapper/EGO，所以不宣称已定位根因。健康阈值保持PROVISIONAL，GOAL B/C/D/F及阶段状态均不变。

验证：#257容器退出码0；`gz sdf -k`报告 `Valid`（保留已有 `gz_frame_id` schema warnings）；run-local两份shell脚本语法和3个Python脚本编译检查通过。收尾时 `python3 tools/project_status.py` 通过；相关8份证据JSON及checklist/milestones解析通过，来源与原始产物哈希472/472匹配，工作区与暂存区 `git diff --check` 通过。原始数据与哈希见[诊断证据](../evidence/p2-stereo-image-freshness-20261020-257.json)。未改项目源码，不运行colcon构建。

下一步保持0.5 m配置，加入直接双目／IMU源龄观察，在mapper/EGO全栈下区分输入源间隙与适配器接收／调度问题；保留健康门，不启动控制器或PX4。
