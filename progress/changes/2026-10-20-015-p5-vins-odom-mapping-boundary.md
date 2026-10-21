# P5 VINS odometry 与 EGO mapping boundary 复测 #221–#224

对话摘要：[2026-10-20-015](../../collaboration/dialogues/2026-10-20-015-p5-vins-odom-mapping-boundary.md)。轻量报告：[run #221](../evidence/p5-vins-anisotropy-filter-imu-horizontal-odom-repeat-20261020-221.json)、[#222启动排除](../evidence/p5-vins-anisotropy-filter-domain-preflight-20261020-222.json)、[#223前置门](../evidence/p5-vins-anisotropy-filter-imu-mapping-boundary-preflight-20261020-223.json)、[run #224](../evidence/p5-vins-anisotropy-filter-imu-mapping-boundary-repeat-20261020-224.json)。

- **改动**：新增 run-local `capture_mapping_boundary.py`，只记录 raw depth、depth-health、转发到 EGO 的 depth/pose、mapping status、occupancy 元数据，不保存图像/点云负载，不发布消息、不订阅真值。#222–#224 的 launcher 只增加 observer、话题端点快照和隔离清单行；没有改 canonical 算法、定位/深度健康门、PX4 参数或控制逻辑。#223 的 observer 初始版本使用了 rclpy 的只读 `subscriptions` 属性，导致初始化失败；改为 `_subscriptions` 后通过编译与消息导入检查，并在 #224 从启动时工作。
- **#221**：六包构建通过；前置门通过并派发目标。raw odometry 捕获945条，源戳11.288–73.592 s、最大源间隔68 ms；定位状态1110条全有效。EGO timeout 后目标 `goal_timeout`，车辆最终落地解除武装。ULog无dropout，EV position 43/49、GNSS flags为零。
- **#222**：六包构建通过后，ROS domain 233 触发 DDS 端口映射错误，PX4 XRCE 未就绪，wrapper以exit 20结束；无导航图或动作目标。此运行只作为配置启动排除记录。
- **#223**：定位在source stamp12.876 s以`telemetry_stale`失效，action未派发；raw odometry仍记录到75.904 s，VINS telemetry到50.228 s。mapping observer属性错误导致没有trace文件，修正后的晚启观察器在容器 teardown前也未落盘。
- **#224**：六包构建、ROS导入、shell/Python预检通过。mapping observer记录1734条raw depth、309条EGO forwarded depth、431条EGO pose、925条occupancy输出和持续READY的depth-health。各源消息流最大观察间隔分别为132/132/100/84 ms；timeout日志中EGO内部同步源戳停在16.768及17.756 s，而输入状态继续。目标派发后在bias=0.150853 m/s²处由既有安全门取消，最终落地解除武装；ULog记录无dropout、EV融合标志25/41、GNSS flags为零，并有AUTO_LAND与触地前DESCEND/failsafe。
- **验证**：#221/#222/#223/#224 各自六包 colcon build 均通过；run-local launcher 通过`bash -n`，observer通过`python3 -m py_compile`及容器内 ROS 消息导入检查；#221/#224 的`analyze_px4_ulog.py`成功生成 landing timeline；每份 evidence report 保存相关文件SHA-256。结构检查、哈希审计与`git diff --check`在完成文档更新后运行。结构检查仅证明骨架一致。
- **解释边界**：#221 与 #223 的 raw odometry 观察证明这些独立运行中原始 VINS odometry 没有完全停发；它们不是 #220 同一 run 的记录。#224 的边界 trace 支持 EGO 内部消息同步/回调交付存在间歇，但额外 ROS 订阅可能影响调度，且该 EGO build缺少 patch 0015 的原始 filter receipt/lost计数，尚不能区分DDS交付、executor调度和同步器处理原因。目标在bias门处中止，不是导航成功。
- **下一步**：为保留 P4 action 集成的 EGO 源构建一个应用既有 patch 0015 的独立 overlay，沿用同目标与全部健康门，使用更少高带宽外部观察器，直接记录EGO现有 message_filters receipt/lost计数后再复测。P5未通过。
