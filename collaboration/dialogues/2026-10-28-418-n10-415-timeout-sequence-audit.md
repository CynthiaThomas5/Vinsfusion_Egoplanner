# N10-20261028-418 对话摘要：#415 原生超时链审计

- 基于 #415 已归档 `vio.log`、`flight.json`、depth-fusion trace 做只读时间线关联。
- sim 121.088 s，localization adapter 因 `propagated_invalid_quaternion` 锁存；EGO最后depth-pose sync计数3408、occupancy更新时间121.080 s。
- sim 121.516 s，EGO 观测到数据龄0.436 s，超过其原生0.400 s超时，终止目标并回报 `planner_full_curve_depth_odom_timeout`。
- 证据支持近因链“VIO/adapter完整性锁存→EGO无新有效depth/pose融合→原生超时→任务中止”；无证据唯一定位无效四元数根因，也不把问题归于紧凑trace序列化。
- 没有改源码、配置、门限或控制状态。#415安全收尾仍需自然终态或新的明确紧急disarm授权；N10继续未完成。
