# N08 #306 后向观察 SITL 健康拒绝

- 后向yaw=−π已到达；回中yaw−π/2期间cost=1.0311887超过原1.0门限。完成12/17阶段，未到yaw0或扫描后N05。
- 初始N05仍拒绝raw ground plane候选不足；无goal/enable/飞行。fixture移除与landed确认，独立PX4 DISABLED/disarmed/landed/control0，容器Exit(0)。
- 无地图后快照，不能判断后向视角效果。#307仅缩短rear hold 12s→4s，观察能否保持健康完成回收，不改阈值。

证据：[运行报告](../../progress/evidence/n08-negative-y-rear-view-health-refusal-20261026-306.md)。
