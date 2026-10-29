# N10.3/#414 校准准备

- **状态：** 静态准备检查通过；ROS 构建、预启动身份检查和 SITL 尚未执行。不能据此判定 N10.3 通过。
- **唯一行为变量：** EGO 常规前视航向速率 cap 从 π 改为 0.10 rad/s（patch 0057）；目标末端 task-yaw 样条保持原实现。固定路线、0.40 m/s 速度、0.25 m/s² 加速度、5 m horizon、1 s lookahead、起点/目标、方箱时刻/尺寸、模型、碰撞策略与验收草案不变。
- **只读地图来源追踪：** patch 0058 默认关闭，仅在 #414 planner profile 的箱体 ROI 启用。输出按融合帧记录源图像/位姿戳、相机位姿、每个 ROI 更新体素的 hit/miss vote、log-odds 和 raw class 前后值；observer 写入 run-local JSONL。追踪不参与地图规划、PX4 控制、起飞/暂停/取消/降落或验收决策。资源结果将注明追踪写盘负载，不直接外推无追踪平台容量。
- **工具身份：** EGO patch 0057 SHA-256 `10253a99a10573a684adaa2d5d183f76234cfef35727122709181ce7239b66a8`；patch 0058 SHA-256 `9f847bcef6dd2384c936491971480a12e806d0794f80c6409d27ed269649d203`；连续 patch replay 0057→0058 与 vendor 目标文件逐字节一致。`tools/test_vio_ego_bringup_config.py` 11/11 通过；新增离线体素 trace evaluator 在缺数据时返回 `INSUFFICIENT`。
- **保留项：** #412 现有 acceptance `INSUFFICIENT`、raw-map 分类 `FAIL`、跟踪/速度预算不足和故障证据保持原样；不删门槛、不加在线健康/资源/known-free 门。所有正式 N15/N16 次数仍在 N10 冻结后。
- **下一步：** 构建当前 source lock 下 ROS 包；仅在容器镜像、planner 配置、PX4 初始 landed/disarmed/disabled/zero-control、goal graph 和 source/runtime hash 均符合预启动记录后，执行 #414 一次 SITL 校准。
