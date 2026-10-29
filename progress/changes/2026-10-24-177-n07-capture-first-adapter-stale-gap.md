# N07.23 #177：覆盖 release gate 到 hover 前置的完整时序

## 执行模式与范围

Goal 完成模式；用户指定范围 N07。父目标保持 in_progress，当前合格悬停计数 1/3。只用当前固定仿真版本验证 N07，不改变代码、参数、健康门、N05 阈值或动作。

## 已有基础与缺口

#176 在新 epoch 中完成 12/12 支架阶段，attached、post-release 和 current-area N05 online/offline gate 均 fresh 一致接受，raw ground plane 有效且地下体素在接地阶段被排除。但 no-goal hover 前置等待持续看到 localization state 4、reason propagated_stale；raw VINS telemetry/odometry 仍更新，adapted optimized odometry 未收到。#176 probe 在 sim 553.636 s 停止，hover runner 首次状态采样从 sim 631.584 s 开始，因此缺少的 553.636–631.584 s 时间窗覆盖了可能的首次失鲜。

## 假设与唯一变量

假设：N05 current-area gate 后、hover 前置开始前发生了可恢复的 raw 输入接收或 adapter 输出时序中断；健康门锁存后，即使 raw stream 恢复也不会在同 epoch 自动复原。

唯一主要变量：沿用 #176 的只读 VIO probe，但保持它从 attached gate 后、release 前启动，持续覆盖 post-release gate、current-area gate 和 hover precondition/hover 结果。支架运动时不运行额外 probe；probe 不发布，不替代任何 gate。

固定镜像、runtime contract、spawn、wall_box_column、separated_return profile、N05 与健康阈值、无目标悬停程序和独立验收脚本。必须新 cold start epoch，不续用 #176 的 stale 状态。

## 完成标准与边界

- 取得 12/12 支架阶段和 attached N05 online/offline 一致 fresh 接受。
- release 后 N05 与 current-area N05 都 fresh 接受且保持同一 epoch/map_id。
- 若 hover precondition fresh tracking，完成至少 30 仿真秒 no-goal hover，并保留独立误差、源/接收/融合时间、PX4 EV/GNSS/ULog、ROS graph 唯一 publisher 和最终 landed/disarmed 证据。
- 若前置 stale，绝不 enable/arm；保存 raw telemetry、raw odometry、raw IMU propagation、adapted odometry/status 和 clock 的首次断点，安全收尾。
- 任一健康锁存或失败都不计入 3 次连续通过，修复后重新计数。不得调整地下规则或阈值。

## 结果

#177 通过，是 #176 stale 前置失败后新连续序列的第 1/3 次。完整证据见[报告](../evidence/n07-no-goal-hover-20261024-177.md)与[结构化报告](../evidence/n07-no-goal-hover-20261024-177.json)。attached、post-release 和 current-area N05 online/offline gate 均 fresh 接受且同 epoch/map；只读 VIO probe 覆盖至 hover 完成，未见 stale。30 仿真秒无目标悬停及独立 N07 11/11 评估通过；PX4 ULog、ROS graph 和最终 landed/disarmed 检查通过。fixture helper 的末尾 fresh DISARMED 检查错误原样记录，postscan 独立 readback、N05 gates 及最终 flight/ULog 状态均确认安全。容器已停止，Exited(0)。

## 下一项

N07.24 #178：使用同一固定镜像、runtime、wall_box_column、分离返程支架路线、N05 门和悬停验收标准启动新的独立 cold start；成功后连续序列为 2/3。任何新 stale、健康锁存或 gate 失败都按原标准重置计数。
