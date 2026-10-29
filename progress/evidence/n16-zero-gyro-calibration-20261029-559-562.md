# N16 #559–562：仿真陀螺偏置校准与新版本绑定

Goal完成模式，用户范围为N16全部出口；至少300sim秒，故障专项排除。#555仍为失败，不因离线结果重计通过。

#559核对实际D435i传感器模型：相机IMU未配置噪声或偏置；PX4自有噪声IMU是另一传感器。候选仅约束已知零陀螺偏置，速度和加速度偏置仍自由；g_norm、噪声权重、运动参数不变。默认关闭。优化器SubsetManifold与边缘化使用一致的六维速度/加速度偏置切空间。仅用于当前理想仿真传感器，不构成硬件校准证据。

#559真实构建PASS，8项数学验证PASS。#560两个完整同输入对照均接收91728条IMU及11119对双目图像、全部处理、零丢弃。默认关闭精确复现旧基线；开启后位置P95从0.279115降至0.100310m，最大0.104996m；末段位置从0.315816降至0.080129m，yaw最大由2.913522降至0.219298度。属于离线证据，不替代真实正式运行。

#561将最小补丁移入隔离生产候选，不迁入离线RELIABLE/输入trace修改。真实colcon vins构建PASS（44.8秒）。仅额外修正只读进程观察器Clock订阅为sensor_data QoS，避免#555记录空时钟，不改变飞行分支。生产根源码尚未迁入本候选。

#562记录补丁应用顺序、源码哈希、GPL许可和构建；生成新运行身份3d3e91ea9124f3b1e422cd1150830aeb18b1bcf54cf9d0bd341013f2bf993383。验收仍为独立0.3m/15度/连续3秒；不删除标准。31项N16相关单元测试PASS。启动#563真实GUI五分钟正式第二次尝试，结果待独立评估。

产物：
- artifacts/n16-prepared/n16-20261029-559-zero-gyro/（构建、8数学测试、来源）
- artifacts/replays/n16-20261029-560-zero-gyro/comparison.json（完整输入、误差）
- artifacts/runs/n16-20261029-561-production-build/（最小生产补丁、构建、前后哈希）
- artifacts/runs/n16-20261029-562-release/（新协议/身份/启动器及旧配置归档）
- 候选 /home/huangxiaocheng/n16-20261029-561-gyro-calibrated/project

验证命令：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -m unittest tools.test_n16_process_lifecycle tools.test_n16_continuity tools.test_flight_profile tools.test_n16_resource_evidence tools.test_n16_contact_scope tools.test_arrival_evaluator（31 PASS）。

未解项：真实完整任务、资源/时序/地图诊断曲线、独立逐项出口审计、正式部署源码归并；N16继续in_progress，N17未开始。运行中只能在落地上锁及独立safe-to-stop全部通过后停止本项目容器。
