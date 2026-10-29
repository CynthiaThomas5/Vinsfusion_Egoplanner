# N08.2aa #237 任务摘要

- #235 桥接 detail 曾读到 `alignment_pair_gap_sim_s=100.392`、匹配对 age=111.949 s；其语义是 PX4 local-position 与 optimized odometry 的源戳差，非直接 PX4 HRT/ROS `/clock` gap。完整事件时序未保存。
- #237 保持 #235 支架扫描、N05/health 门限不变，只加只读 recorder，记录 ROS clock、定位/VINS/raw 与 adapter odom、map 和 PX4 bridge time diagnostics。允许同身份准入后执行 compute-only；不做 XY。
- 结果：22-stage scan 到达 rear-down view，返程 yaw 阶段 16/22 因 LocalizationStatus `normalized_cost_exceeded`（0.95343→1.013814）停止。N05 before 仍拒绝 `ground_plane_insufficient_raw_occupied_voxels`，无 post-release gate 或 compute-only。
- HRT 与 `/clock` 差 −8 至 +16 ms、PX4 time domain 始终有效。LocalizationStatus 锁存后 adapter optimized/propagated odometry 停在 474.048/474.148 s；raw VINS/odom 继续到 515.364/515.432 s；local-position/adapter pair gap 增至 41.376 s、bridge `localization_not_tracking`。大 gap 为定位锁存之后的结果，本次未发现 HRT/ROS clock 是触发源。
- 全率首段因事件量过大提前以 stop marker 收尾，第二段改为 100 ms 有界采样；两段之间有 sim 52.740–251.428 s 数据间隔，但关键 health-to-pair-gap 转换完整捕获。夹具移除、landed/DISARMED，容器停止。详见 [evidence](../../progress/evidence/n08-time-pair-timeline-20261024-237.md)。
