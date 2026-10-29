# N08 #286：缺少 N05 扫描时的准入拒绝

本次误将 N08 mission 直接用于新冷启动，没有先执行 N05 全机支架扫描和释放后准入流程。40.0 秒只读 preflight 通过，但 mission 当前区域 N05 在线检查因 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` 拒绝；离线重放与在线结果一致。没有进入 N08 runner、没有发送 goal、没有启用控制或起飞。

4 秒 PX4／bridge 只读回读为 `DISABLED`、`armed=false`、`control_enabled=false`、`landed=true`；PX4 `arming_state=1` 且 LandDetector 为 landed。回读期间 OffboardControlMode、TrajectorySetpoint、VehicleCommand 消息数均为 0。项目容器通过项目 stop 正常退出；没有停止其他容器。

这是扫描顺序遗漏造成的前置拒绝，不是 N08 曲线或取消试验结果。完整输入、原始在线／离线报告及回读见 [机器报告](n08-n05-prescan-order-refusal-20261026-286.json) 和 [#286 运行产物](../../artifacts/runs/n08-cancel-translation-prescan-20261026-286/)。
