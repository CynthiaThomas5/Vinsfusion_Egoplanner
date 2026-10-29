# N08 #312：慢返程通过，后向观察后的下降触发健康拒绝

状态：未通过；没有释放后 N05、N08 mission 或飞行。

## 假设与唯一阶段变量

沿用 #311 的 rear-facing short-hold 扫描和 12 s 下降，只把第 7 阶段从 x=−1.2 m 回原点的时间 60→100 s。假设慢返程能降低阶段间变化的视觉残差尖峰；健康阈值和其他门保持不变。

配置测试 43/43 通过，结构检查通过。新冷启动 profile 共 17 阶段，实际完成 14 阶段：

- 第 7 阶段在 100 s 内从 x=−1.2 m 返回原点，未触发锁存；该段 trace 最高 normalized cost=0.698737。
- 负 Y 侧视、yaw=−π 后向观察以及 yaw 回到 0 均完成。回中后的 12 s 水平保持末值 normalized cost=0.795303。
- 在接下来的 z=1.0→0.5 m 下降开始约 5.1 仿真秒后，VINS 健康门于 sim 456.628 s 锁存 `normalized_cost_exceeded`，值=1.005560>1.0。最后支架 trace 约 z=0.813 m、cost=0.959464。
- 锁存快照的 optimized/telemetry 源龄约 136/72 ms，`stale_observation=null`；prior evaluation 与 spectrum 均通过。cost 分组为 visual 1071.87/5216、IMU 132.86/150、marginalization 1549.64/82 residuals。

## 判别与限制

本轮支持“第 7 段慢返程能越过 #309/#311 的早期返程拒绝”，但没有解除回正后下降阶段的健康锁存。#307 的 8 s 下降在 z≈0.899 m、cost=1.009861 失败；更早 #248 的 20 s 下降也在相近高度附近 cost=1.037158 失败。因此停止继续单纯延长下降时间。#312 与 #307 阶段 trace 显示，下降前健康代价分别约 0.795 和 0.899，进入垂直运动后持续上升；这提示后向观察后的下降时序／观察几何需要另行判别，不能归因于固定速度阈值。

初始 N05 baseline 仍因 `ground_plane_insufficient_raw_occupied_voxels` 被 online/offline 一致拒绝。支架被 detach，Gazebo model list 未见 fixture，LandDetector 为 landed。清理记录因 fixture 命令缺少 fresh DISARMED 状态而未达到 helper 自身的清理确认；独立 6 s 只读读回确认 bridge `DISABLED/control_enabled=false/armed=false/landed=true`、PX4 `arming_state=1`、landed=true，OffboardControlMode、TrajectorySetpoint、VehicleCommand 均为 0。只停止 #312 容器，退出码 0；无 goal、enable、post-release N05、N08 mission 或飞行。

下一项：保持阈值不变，先完成低位回收，再在低位以略向上的后向视角观察后方薄层；不在后向观察完成后执行下降。新图仍必须通过同身份 post-release/current-area N05、40 s preflight 及实时前向几何，才有资格进入 motion-cancel 测量。

机器摘要：[JSON](n08-rear-scan-health-refusal-20261026-312.json)。原始运行目录：`artifacts/runs/n08-cancel-highspeed-prescan-20261026-312/`。
