# #246 N08 定位新鲜度诊断摘要

## 任务

在保持 planner 与证书门限不变的情况下，复跑 #245 的慢回程 N08 compute-only profile，判断 PX4 HRT／ROS 时间参考或定位 freshness 是否继续阻挡 N08，并记录曲线证书拒绝原因。

## 决定与约束

- #245 的 stale lockout 原因仍未证实；不放宽 0.300 s 定位门限。
- PX4 HRT／ROS 有效性、LocalizationStatus 新鲜度和 N08 曲线证书分开判断。
- 未通过同 run 曲线速度／地图证书时不执行 XY 或制动实验。
- N07 累计通过的 #198/#200/#204 保留，不复测。

## 结果

#246 的 PX4 HRT／ROS 266/266 有效、零时钟回退，LocalizationStatus 304/304 有效，#245 的 stale 未复现。compute-only 的目标、READY、取消、hold、落地检查通过；曲线证书仍因 x 轴导数控制上界超过单轴速度门和起点 hold 球 100 个地上 unknown 而拒绝。没有 XY 或制动数据。独立末态读回确认落地上锁且 fixture 已移除，容器停止成功。

## 下一步

#247 在已成功的慢回程 N05 profile 上加入负 Y 观察、停留和回中；其唯一主要变量是视角覆盖。速度配置、地图阈值和安全半径不变。
