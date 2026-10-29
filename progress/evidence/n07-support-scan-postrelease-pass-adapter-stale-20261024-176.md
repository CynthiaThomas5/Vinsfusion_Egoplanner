# N07 #176：N05 gates 通过，定位传播失鲜阻止无目标悬停

## 结论

#176 在新 cold-start epoch 中完成 12/12 全机支架扫描。attached、支架移除后的 released、以及起飞前 current-area 的 N05 online gate 均 fresh 接受，offline replay 完全匹配。地下体素按已确认的 raw ground plane 从接地阶段飞行体积中排除，未把地下作为可飞 free space。

但 no-goal hover 前置等待发现 localization status 已持续为 propagated_stale，adapted optimized odometry 没有输出。hover 脚本 fail-closed 地在 enable/arm 前退出；没有飞行、悬停或 N07 合格次数。父 N07 保持 in_progress，计数仍为 0/3。

## 运行身份与地面规则

- Run：n07-20261024-176-01；epoch 11fbad21e62a415a9d365c483e6003e1。
- 固定镜像 SHA-256：099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8；runtime contract SHA-256：856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb。
- 布局 wall_box_column，spawn -6.5,0,0.3,0,0,0，profile n06_full_airframe_retreat_240_oblique_separated_return。健康阈值和 N05 标准未改。
- 初始 raw-map 检查因 ground_plane_insufficient_raw_occupied_voxels 拒绝：当时没有足够 raw occupied floor voxels 可靠拟合地面，因而没有凭未知体素猜测地下边界。
- scan 后 raw occupied plane 有效，z=−0.25 m，114 个 floor voxels 支持拟合。TAKEOFF_CONTACT、ASCENT、HOLD、DESCENT、LANDING_CONTACT 各阶段最大 unknown/occupied 为 0；接地阶段地下体素最多排除 89 个，ASCENT/DESCENT 各最多排除 75 个。这个规则排除地下区域，不表示允许向下飞行。

## 支架扫描与 N05 gates

支架到达 12/12 阶段，ready marker 显示 attached、PX4 DISARMED、没有 truth 输入和 control/goal 发布。fixture-trace.jsonl 的 15414 条记录全为 TRACKING/valid，epoch 未变，normalized cost 最大 0.754195；raw VINS telemetry 的 2772 条记录均为 finite、current、solver usable，accel-bias 最大 0.127334 m/s²。

fixture runner 最后报告 localization changed or became invalid during physical scan，并保留 outcome=failed。错误发生在夹具已 detach、Gazebo remove 已确认后，runner 的最后等待步骤；不得把该辅助 runner 报告改写为通过。独立安全回读显示 fixture 模型已不存在，PX4 DISARMED/landed，bridge DISABLED。

三个 N05 live reports 分别是 attached、post-release、current-area，均为 accepted=true / all_entry_phases_known_and_clear；三份离线回放都匹配 online，epoch/map_id 始终为：

11fbad21e62a415a9d365c483e6003e1 / 11fbad21e62a415a9d365c483e6003e1-32097c2f7c63471cb13721e9faa6b0d0

post-release freshness 为 snapshot/source/fusion 0.092/0.124/0.028 s，current-area 为 0.092/0.132/0.036 s，均低于 0.4 s 限值。

## 定位失鲜与安全退出

attached gate 后启动的只读 stream probe 覆盖 195.68 墙钟秒、sim 405.524–553.636 s。raw telemetry、raw odometry、raw IMU propagation、adapter optimized/propagated odometry 与 localization status 均无 gap event，status 保持 TRACKING。probe 在 current-area gate 和 hover runner 之前停止，因此没有覆盖实际失鲜转换。

随后 run_vio_no_goal_hover.py 运行 61.25 墙钟秒，始终未满足前置，失败原因为 vio_bridge_map_preconditions_not_ready。该窗口：

- 1201/1201 条 localization status 均为 state 4、valid=false、propagated_stale；status header 从 sim 631.584 s 前进至 677.384 s，但 source_stamp_ns 始终停在 626.256 s。
- raw VINS estimator telemetry 有 694 条；solve_current、solver_usable、state_finite 全部为 true，normalized cost 为 0.461660 附近。
- raw VINS odometry 有 768 条，source stamp 从 626.772 s 持续到 677.392 s，接收间隔最大约 0.126 s。
- depth health 保持有效。read-only alignment recorder 没收到任何 /localization/optimized_imu_odom 样本。
- service_calls=[]、action_goal_sent=false，没有 enable、arm 或 navigation goal。

失败后额外只读采集 20 秒：raw imu_propagate、telemetry、odometry、IMU、双目与深度再次连续（各流 gap event 为 0），但 localization status 仍是 propagated_stale。因此已确认失效时 raw telemetry/odometry 存在、adapted optimized odometry 缺失；首次使健康门锁存的具体输入 gap 尚未被捕获，不能断言 root cause。

最终 direct readback：bridge DISABLED/unarmed/landed，PX4 arming state 1、landed true，支架模型不存在；bash tools/project.sh stop n07-20261024-176-01 后容器 Exited (0)，没有活动项目仿真。

## 后续动作

#177 使用同一版本、profile、布局和阈值；不在支架运动时运行 probe。attached gate 通过并释放后，probe 保持运行并覆盖 post-release、current-area N05 与 hover 前置。首个定位状态或 stream 不 fresh 时继续拒绝起飞；只有实时 gate 和 precondition 都通过才进入至少 30 仿真秒无目标悬停。

完整数据与 SHA-256 见 [run directory](../../artifacts/runs/n07-20261024-176-01/)、[改动记录](../changes/2026-10-24-176-n07-postscan-source-timeline.md)和[对话摘要](../../collaboration/dialogues/2026-10-24-176-n07-postscan-source-timeline.md)。
