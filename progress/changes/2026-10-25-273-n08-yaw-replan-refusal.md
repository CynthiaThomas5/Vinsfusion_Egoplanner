#273：N08 转向中途重规划诊断与归档

- 本轮完成#273正确低速profile下的新cold-start运行。N05 post-release/current-area准入、40秒preflight、takeoff settle、0.6m前向EGO制动测量及0.22m前向转向定位段均取得结果；定位状态回执空窗未复现。
- 实际失败位于定点180° yaw过程：EGO重发从当前yaw继续到目标的部分样条，当前watchdog仍要求每条样条从原始yaw完整覆盖π，因此拒绝并请求降落。该重规划的保守yaw率界约2.4386 rad/s，也高于既定0.5 rad/s界，需保留此约束并修复规划时长／重规划契约。
- 同一阶段，EGO/VIO估计位置变化0.02975m，bridge alignment漂移最大0.01011m；独立真值相机位置却偏移0.20949m，VIO-真值误差最高0.20054m，健康状态仍为valid。PX4 setpoint从yaw轨迹首个生效样本起移动0.22376m，与0.12m机头传感器杆臂旋转补偿的理论0.22378m吻合；设定点变化是预期映射，VIO/PX4与真值之间偏差的物理原因仍未定位。
- 用户明确普通goal到达即结束；如需返航，转头和返航是单独命令／第二段航线。#273 N08专用往返runner分别发送去程、yaw和home三个`NavigateToPose` action；去程成功，yaw失败，home未发送。这是验收场景的自动编排，不是普通goal的隐式行为。
- 对照GOAL／N08正式出口：普通目标不要求返航到home pad。#273的yaw失败属于runner随后编排的独立第二段；去程制动数据保留。#260/#267/#273都有独立制动记录，但runner和goal配置fingerprint不同，不能拼成同版本3次重复。N08正式缺口仍为受控机制解释／修复、运动中取消停止／保持、同版本3次普通单目标冷启动和N05/N06预算回填。
- 清理#273机器摘要中过时的顶层`remaining`字段，避免把返航诊断和N08单目标正式出口混写；分别保留`formal_n08_exit.remaining`与`separate_return_workflow.remaining`。
- 未修改飞行控制代码、门限或Goal契约。本轮只补充证据、changes、dialogue、milestones及CURRENT；父N08保持`in_progress`、`next_goal=N08`。
- 验证：原运行`n08-20261025-273-observer-pre-enable-repeatability`的独立制动报告为FAIL（制动数据检查通过，yaw／return/完整性检查未通过）；离线复算了VIO、bridge alignment、PX4 setpoint与真值的同一转向时间段；`git diff --check`通过，证据JSON和milestones JSON解析通过。
- 局限：observer移除后本轮状态间隔正常，只支持此前假设，不构成因果证明；VIO/PX4估计与真值的转向位置差异根因未确定；未完成航向确认、fresh post-turn地图检查、机头前向返航、运动中取消制动或三次完整冷启动重复。
- 对话摘要：[`#273`](../../collaboration/dialogues/2026-10-25-273-n08-yaw-replan-refusal.md)。
- 证据：[`报告`](../evidence/n08-yaw-replan-refusal-20261025-273.md)，运行目录`artifacts/runs/n08-20261025-273-observer-pre-enable-repeatability/`。
