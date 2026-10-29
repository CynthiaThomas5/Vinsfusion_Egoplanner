# #362 N10.3 当前 gate-free runtime 高速取消停车重复

对话摘要：[2026-10-27 #362](../../collaboration/dialogues/2026-10-27-362-n10-gatefree-braking-repeat.md)

## 目标和固定输入

按 #359 的 0.50–0.56m/s PX4水平速度窗、同 EGO route/planner/spawn/official_ego 重复 caller-cancel 实测；唯一主变量为当前 runtime 直接删除项目定位质量/回执龄门限（#359 使用旧实现的 run-local 旁路）。真实速度、曲线、停车距离和来源时序由独立观察器记录。

## 验证

- SITL 前 runtime contract：`fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`，665 files，与 #361 相同。
- 既有 17 包构建及 413 项单测和两项 ROS 集成适用于该指纹；本项不改源码/配置。
- 协议及启动前指纹：[#362 protocol](../evidence/n10-cancel-stop-gatefree-speed050-protocol-20261027-362.md)。

## 运行结果

SITL 已完成。`n10-cancel-braking-evaluation.json` 的 `measurement_complete=true`，11/11 检查通过；caller-cancel 下 `action_canceled=true` 且 `action_success=false` 是预期试验结果。触发 PX4 水平速度 0.500180m/s、EGO 参考速度 0.533871m/s；替代轨迹延迟 0.032 仿真秒；6.76 仿真秒进入停止带，真值水平路径 1.260994m、端点位移 0.990563m。禁止接触0，五观察器覆盖终态，独立 landed/disarmed/control-disabled/zero-control 读回及 `safe-to-stop.json=true` 均通过，之后按项目入口停止容器。

与 #359 的单个旧样本相比，路径短约 0.04348m（3.3%），但进入停止带慢 1.80仿真秒；两个样本不足以得出一般停车保证。#362运行在含静态场景的世界，但该次报告没有单独计算障碍物净空，也没有动态障碍重规划或故障退出证据。完整结果见 [#362 evidence](../evidence/n10-cancel-stop-gatefree-speed050-20261027-362.md)。N10.3/N10 保持未完成。
