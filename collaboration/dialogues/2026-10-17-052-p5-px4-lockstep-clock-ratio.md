# P5 PX4 lockstep 与 Agent 时基对照

- 用户目标仍为完成 GOAL.md 全部 P0–P6 与 A–H；本次只做本地被动 SITL，不修改 PX4 来源、控制行为或健康门，不启动真机。
- #113 保留 PX4 lockstep、Gazebo D435i 模型、XRCE Agent 和 DISABLED bridge，省略 VINS/localization 计算，运行45秒，ROS domain 229、新 partition/build副本。
- #113测得 `/clock` 速率1.000005、observed_offset斜率−0.000003、无滤波器 reset；#112全VIO负载下为0.417598、−0.582393、两次 reset。速率斜率关系接近 `offset_rate = RTF - 1`。
- #113没有视觉里程计或EKF融合，不能作为P5/P6通过；待做全栈 CPU 与 RTF profiling，判断如何在不放宽门控的条件下保障时间映射。
