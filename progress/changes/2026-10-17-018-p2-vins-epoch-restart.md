# P2 实际 VINS 进程重启与 epoch 隔离

日期：2026-10-17。对话摘要：[2026-10-17-018-p2-vins-epoch-restart.md](../../collaboration/dialogues/2026-10-17-018-p2-vins-epoch-restart.md)。

- 新增：`tools/probe_vins_epoch_restart.py` 与两份独立 run-local harness；分别运行于 ROS domain 195/196 和不同 Gazebo partition。每次在 localization TRACKING 且 EGO 地图非空后对实际 VINS 进程发送 SIGINT，观察旧 session 锁定、map 清空与输出稳定，再启动带新 manifest/epoch 的 VINS 与 localization adapter。
- 结果：两次均通过。旧 VINS publisher 消失后 localization 为 `LOCKED / optimized_publisher_missing_or_ambiguous`；EGO occupancy 变空，depth/pose 与定位 odometry 计数在确认窗口保持不变。新 epoch 先观察到空图，然后恢复 TRACKING 并重建非空地图；其后 37/19 条 EGO pose 与 298/458 条 odometry frame 均只包含新 epoch frame ID。运行、初始图点数、时间、计数、manifest 与关键日志 SHA-256 见[轻量证据](../evidence/p2-vins-epoch-restart.json)，原始数据位于 `artifacts/runs/p2-vins-epoch-restart-20261017-01/` 和 `...-02/`。
- 验证：两份 runner 均在固定派生镜像内 exit 0；runner `bash -n` 通过；定位与建图自维护运行源哈希逐一匹配对应安装 overlay；容器进程审计未发现仍运行的 VINS、plan_env、定位、建图或 Gazebo 进程（仅历史 defunct VINS）。最终 JSON/hash、结构检查与 `git diff --check` 在文档更新后复核。未改生产节点源码，无需重跑 colcon。
- 局限：两次独立运行证明真实 VINS 停止／新 session epoch／map reset 的仿真行为，不覆盖任务目标或轨迹取消、PX4 Offboard/Land 故障动作、10 分钟负载、规划闭环、相机实物标定或实机。GOAL E、P2、P4 仍进行中。
- 下一步：检查 GOAL D/E 与现有接口契约，落实 localization epoch/validity 变化时目标与轨迹的取消状态；保持 `uav_px4_bridge` 是唯一控制设定点发布者，然后用 ROS 集成测试验证 reset 期间不会续接旧目标。
