# #391 收尾与漂移复核摘要

## 用户决定

- 授权一次紧急 SITL disarm 并受控停止；仅用于结束已处于 armed/failsafe 且未确认 landed 的 #391 会话。紧急命令前最近 PX4 nav_state 为 DESCEND（12）；此前状态历史短暂记录 AUTO_LAND（18）。
- 保留 #391 失败分类。紧急收尾不能倒算成原生 planner fault landing，也不计 N15/N16 正式次数。
- 继续调查真实断流、EGO 输入超时、planner 退出后的终态路径；漂移/跟踪误差要结合场景几何判断，不能仅删掉门限。

## 本轮结果

独立 3 秒 readback 确认 bridge LANDED、PX4 disarmed/landed、control disabled、控制输出零；随后项目 stop 正常退出且无匹配活动容器。原始 #391 运行和 `safe-to-stop.json` 未改写。

新增固定 prestream 对齐的 hold 离线比较：首次接触前 PX4 local position 仍贴近 trajectory setpoint，而 raw VINS 与真值位置误差持续增加；feature/long-track 计数降低。此证据支持估计/测量与实际运动分离，但没有失败保持期间相机图像和 stereo receipt 历史，故不能唯一归因于视觉视野、传感器投递或估计器内部退化。

## 待办

下一步从代码审计定位 planner timeout/process exit 之后的 bridge 与 PX4 状态转换；之后再决定最小实现修复和校准设计。N10 保持 `in_progress`，不恢复用户已排除的经验运行门，不提前运行 N15/N16 正式矩阵。
