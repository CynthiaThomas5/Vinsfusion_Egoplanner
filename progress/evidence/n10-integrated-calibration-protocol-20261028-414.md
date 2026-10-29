# N10.3/#414 校准协议

- **假设：** 在 #412 固定路线中，仅把 EGO 常规前视轨迹航向速率上限从 π 降至 0.10 rad/s，可能减少快速转向片段中的 VIO 相对漂移。#413 的 yaw/RPE 关系是重叠窗口上的描述性关联，不代表因果。终端 task-yaw 样条不受此 cap 限制，单独评价。
- **唯一行为变量：** EGO 常规轨迹航向 cap。速度 0.40 m/s/轴、加速度 0.25 m/s²/轴、5 m horizon、1 s 前视、起点/目标、障碍触发与几何、模型、控制和验收值均与 #412 相同。
- **只读记录：** 记录每个 occupancy cloud 至快照 source-watermark freeze；订阅 depth-fusion 与 ROI voxel-update trace，保留源戳、相机位姿、每格 hit/miss、log-odds 和 raw 分类前后值。新增记录不参与起飞、暂停、取消、降落或控制判断。
- **资源解释：** 启用 per-voxel publisher 和 JSONL 写盘会增加 mapper／observer 负载；#414 的资源数据描述的是带追踪的综合校准，不能直接作为无追踪运行的容量基线，也不据此新增运行门。
- **判据：** 使用原 `config/acceptance.json` 草案和同一独立 3 s joint position/yaw dwell；分别报告运动、保持和降落数据。若不能到达或指标超候选值，保留失败并按证据诊断实现；不删除阈值。
- **安全：** 一个固定时刻的方箱注入；PX4 native preflight/EV 融合及 EGO 原生碰撞和 watchdog 保持。正常自然终态后独立读回 landed/disarmed/control-disabled/zero-control 并确认 `safe-to-stop.json`。本次无故障注入，不使用紧急 disarm。
- **身份：** [协议 JSON](n10-integrated-calibration-protocol-20261028-414.json)、新 profile、patch 0057/0058、启动后 runtime contract 及 run-local 工具冻结绑定；校准不计正式次数。
