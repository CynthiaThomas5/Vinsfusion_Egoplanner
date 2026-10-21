# P2 EGO pose publisher / reader 同窗追踪 #346

对应对话摘要：[2026-10-21-013](../../collaboration/dialogues/2026-10-21-013-p2-ego-pose-publisher-reader-paired-trace.md)。轻量报告：[paired-trace evidence](../evidence/p2-ego-pose-publisher-reader-paired-trace-20261021-346.json)；原始日志、逐条时间线和分析位于 `artifacts/runs/p2-ego-pose-publisher-reader-paired-trace-20261021-346/`。

## 变更

- 仅新增 #346 run-local 低带宽观察器，订阅 `/mapping/status` 与 `/drone_0_camera_pose`，记录系统墙钟、仿真时钟、源 stamp、MapStatus 转发计数；不订阅真值或控制话题。
- 复用 #345 已构建 EGO overlay 和同一实验补丁顺序；复核 EGO binary SHA-256 未变。没有修改自维护 adapter、EGO canonical source、QoS、ApproximateTime 同步器或 0.4 s freshness 门。
- 保留首次 preflight 失败日志：run-local 脚本最初引用未复制到新目录的 overlay；修正为明确复用 #345 overlay 后，Gazebo/VINS/EGO planner-only run 正常完成。

## 结果

- 52 条 EGO timeout 日志形成两段 pose 回执平台。第一段仿真时间 9.620–10.828 s（墙钟 1.800 s）：EGO pose/sync 均停在 116、最后 pose stamp 9.109 s；EGO depth 计数 129→165。该窗口独立订阅收到 36 条相机位姿，源戳 9.571–10.726 s、最大间隔 33 ms；窗口前后 adapter MapStatus 的 forwarded count 为 125→166，epoch/map_id 不变且 `input_ready=true`。两路 EGO RMW message-lost 计数均为 0。
- 第二段仿真时间 22.623–23.097 s（墙钟 0.700 s）：EGO pose/sync 停在 459、最后 pose stamp 22.111 s；depth 495→507。独立订阅收到 12 条相机位姿，源戳 22.573–22.969 s；adapter forwarded count 为 492→509，MapStatus 持续 ready。两路 EGO RMW lost 计数仍为 0。
- 这把观察到的缺口从 adapter-wide 停发缩小到 EGO pose `message_filters` 订阅／回调交付或调度路径；未区分 Fast DDS reader readiness/history 与 ROS executor/callback 调度，也未确认根因。源码审查发现 EGO 节点通过默认单线程 `rclcpp::spin` 运行，深度和位姿订阅在同一个 GridMap 节点内；这提供调度背景，不构成因果证明。
- 本轮随后发送 epoch 绑定 3D 目标并收到 1 条 B-spline。独立 de Boor 检查使用同 epoch/map_id/frame 快照，快照比 spline start 晚 72 ms、深度源龄 69 ms；103 个中心线样点中 41 个落在同一个起点 unknown voxel、62 个 known-free，occupied/inflated/out-of-map 均为 0。起点 voxel 仍仅由实验补丁 0033 放行，轨迹没有执行，也没有机体扫掠净空证据。

## 验证

- `python3 -m py_compile observe_pose_reader_trace.py analyze_reader_trace.py analyze_spline_snapshot.py`：通过。
- `python3 analyze_reader_trace.py`：52 条 timeout 日志、两段回执平台；adapter 转发计数、外部 PoseStamped 收件和 EGO depth 计数的四项窗口判断均通过。
- `python3 analyze_spline_snapshot.py`：8 项只读快照／中心线诊断检查通过；未知样点只落在起点 voxel。该检查不是机体净空验收。
- `./run-container.sh`：Gazebo D435i、VINS、定位/建图和 EGO planner-only run 以退出码 0 完成；runtime summary 未发现 truth/control 话题、控制节点、轨迹服务器或 PX4。

## 限制与下一步

独立 PoseStamped reader 是新增观察负载；单次复测不能确定根因。服务快照与规划器内部使用的栅格不是同一缓冲区字节快照。unknown fail-closed 不变，GOAL C 仍 pending。下一步在不改 QoS 与 freshness 门限的前提下，追踪 EGO depth/pose RMW reader readiness、sample lost/rejected 与 callback 时间线，并配对复现；稳定前不把这条诊断当作 GOAL C 规划或安全通过证据。
