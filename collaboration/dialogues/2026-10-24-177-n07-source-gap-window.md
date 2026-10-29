# N07 #177：捕获 post-release stale 的首个时序断点

## 用户约束

- 用户已授权 Goal 完成模式，范围为 N07，继续到 N07 出口通过。
- 支架移动期间不启用额外时序 probe；N05 释放后 gate 不 fresh 接受不飞。
- 地下空间不属于飞行体积。继续使用已确认的 raw-ground boundary 排除规则，不改 N05 ground semantics。
- 不改固定镜像、runtime、阈值或 no-goal hover 验收标准。

## 决定

#176 的 attached、released 与 current-area N05 gates 均 fresh 通过；地下 cell 被正确排除。hover precondition 之后锁存在 propagated_stale：raw VINS telemetry/odometry 仍新鲜，adapted optimized odometry 未输出。#176 只读 probe 在 sim 553.636 s 结束，而 hover recorder 从 sim 631.584 s 才开始，因此首次状态变化没有被探针覆盖。

#177 使用同一配置的新 cold start，只延长 probe 的 post-scan 观测窗口，持续覆盖 N05 current-area 到 hover 前置。任何 gate 或 localization tracking 失败都保持 fail-closed；只有满足实时 N05 和定位前置后才执行 30 秒无目标悬停。

## 当前状态

N07 仍为 in_progress，连续合格悬停 1/3。#177 完成新 cold start：attached/post-release/current-area N05 online/offline gates 同身份 fresh 通过；只读 probe 覆盖到 hover 结束且未见 stale；30 仿真秒无目标悬停、独立 N07 11/11、ULog EV/no-GNSS、ROS graph 唯一控制者及最终 landed/disarmed 均通过。支架 helper 的 fresh DISARMED 末尾错误和独立安全 readback 均保留。证据：[报告](../../progress/evidence/n07-no-goal-hover-20261024-177.md)。下一项 #178 新 cold start。
