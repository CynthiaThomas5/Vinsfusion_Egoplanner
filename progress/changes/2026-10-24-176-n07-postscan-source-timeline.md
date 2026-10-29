# N07.22 #176：attached gate 后的 release 时序诊断

## 执行模式与范围

Goal 完成模式；用户指定N07，父目标仍`in_progress`，连续合格数0/3。#175完成12/12支架和attached N05 gate，但release后adapter锁存`telemetry_stale`，post-release gate缺少odom。#175单次回读显示raw VINS之后重新新鲜，而adapter仍锁在source stamp 435.304；runner原生日志在sim约399–402s还有一次2.772s gap，但不能证明adapter接收端也发生该gap。

## 假设与唯一主要变量

假设：#175 post-release stale可能由support scan结束后raw输入断档、adapter接收／处理停止或发布间歇引起。唯一诊断变量为只读probe的启用时段：支架运动及attached gate期间不运行额外probe；attached N05 online/offline fresh接受后，在fixture detach与post-release gate之前启动已有`probe_vio_stream_freshness.py`，持续记录raw VINS telemetry/odometry、adapted optimized/propagated odom、status及clock。probe无publisher，不能替代任何gate。

固定镜像/runtime、wall layout、spawn、分离返回profile、健康门、N05标准与hover程序。必须新cold-start epoch；旧#175锁存状态不续接。

## 完成标准

同epoch先完成12/12支架和attached N05 online/offline一致fresh接受，再detach并取得fresh post-release N05正向gate。只有gate通过且hover前置仍fresh，才停止probe并运行至少30仿真秒no-goal hover及N07全部独立误差、PX4融合／无GNSS、ROS graph唯一控制者／无truth、最终landed/disarmed证据。任何health lock、缺odom或gate拒绝都不飞；保存首次raw/adapted时间断点并安全停机；不改门限。

## 结果

## 实际结果

#176 使用固定镜像和 runtime contract、新 epoch 11fbad21e62a415a9d365c483e6003e1，布局 wall_box_column，profile n06_full_airframe_retreat_240_oblique_separated_return。没有改代码、参数、健康门或 N05 阈值。

12/12 支架阶段完成，attached N05 online/offline 一致接受。支架脱离和从 Gazebo 移除后，post-release N05 再次 fresh 一致接受；停止时还复跑 current-area gate，也保持同 epoch/map_id 并通过。raw occupied ground plane 位于 z=−0.25 m；五个入口阶段最大 unknown/occupied 均为 0，接地阶段将 75–89 个地下体素排除。地下没有被作为可飞空间，见 [#176 证据](../evidence/n07-support-scan-postrelease-pass-adapter-stale-20261024-176.md)。

fixture runner 在 12/12 和移除夹具之后的末段 step() 报告 localization changed/invalid，故其 outcome 保留为 failed；15414 条已记录轨迹样本仍全为 TRACKING/valid。独立回读确认夹具模型不存在，PX4 DISARMED、landed，bridge DISABLED。

释放后的只读 probe 连续观测 195.68 墙钟秒，覆盖 sim 405.524–553.636 s；期间 raw 与 adapted VIO 各流都没有 gap event，状态保持 TRACKING。随后 current-area gate 仍 fresh 通过，但 hover runner 在未 enable 前等待 61.25 秒，1201 条定位状态全为 propagated_stale，source stamp 固定于 626.256 s。该窗口 raw telemetry 有 694 条有效/current 样本、raw odometry 有 768 条且持续到 677.392 s，depth health 也持续 valid；alignment recorder 没有收到任何 /localization/optimized_imu_odom 样本。失败后另采 20 秒 probe，raw IMU propagation、telemetry、odometry、相机和深度都重新连续，而 localization 状态仍为 stale。现有证据将故障定位到 N05 gate 之后的定位适配输出/健康链路，但尚不能确定首次 gap 或触发源。

hover 工具因 vio_bridge_map_preconditions_not_ready 退出；没有 service call、arm、navigation goal 或 airborne sample，N07 不计通过，连续合格数仍为 0/3。桥接维持 DISABLED，PX4 DISARMED/landed；项目容器按 stop 流程以 exit 0 结束。#176 的 gate 正向结果不代替 N07 飞行出口。

## 下一步

#177 保持当前镜像、runtime、场景、profile 和门限；支架移动期间仍不运行额外 probe。attached gate 通过并释放后启动同一只读 VIO stream probe，并保持到 current-area gate 与 hover 前置结束，用来捕获 553.636–626.256 s 之间缺失的首个 raw/adapted 断点。若定位未 fresh TRACKING，继续 fail-closed、不解锁；只有实时 N05 和定位前置都 fresh 时才执行 30 秒无目标悬停。
