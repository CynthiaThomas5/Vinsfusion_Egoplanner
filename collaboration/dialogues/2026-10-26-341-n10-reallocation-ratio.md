# N10 #341 reallocation ratio 修正验证

- **触发证据**：#340 显示最终 spline 的 X 轴控制点速度超限；实际加速度远低于门限，但 violation-only `max_acc` 仍是 `-1`，旧式 `sqrt(abs(max_acc)/limit_acc)` 产生 2.0 的 refine ratio。
- **任务与假设**：修正“没有加速度违反时该项对时间重分配的贡献”，再执行同 #340 的长程目标和限制一次。不是调速度值，也不改变原可行性门。
- **授权与边界**：用户已授权完成 N10。只用单 D435i Gazebo/PX4 SITL；真值只读；`uav_px4_bridge` 独占控制；无关容器和实机不动。
- **判据**：检查 no-acceleration-violation ratio 变成0；若后续 final curve 仍超原 X 速度门则记录假设被否定并安全着陆。意外达到 goal 时执行全部原 dwell/600s hold 条件。
- **结果**：patch 0051 编译成功（17/17），新鲜 SITL 中 `acceleration_ratio=0` 确认修复生效；但原目标仍因 X 轴速度拒绝，最终 max 控制点导数 0.305505 m/s > 0.1051 m/s 原门。没有 READY 曲线／水平运动。
- **末态**：contact evaluator 通过、违规接触 0；PX4 arming_state=1，bridge LANDED/disarmed，项目容器停止 exit 0。
- **下一步**：基于两次观测到的 0.239–0.306 m/s 控制点速度，单独试验 planner `max_velocity=0.31 m/s/axis`；对实际命令和 PX4 速度保持 N10 的 0.12 m/s 上限，超限即失败，不抬验收阈值。
- **证据**：`progress/evidence/n10-spline-reallocation-ratio-20261026-341.md`；运行目录 `artifacts/runs/n10-20261026-341-spline-reallocation-ratio/`。
