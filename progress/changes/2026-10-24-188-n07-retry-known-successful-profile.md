# N07.34 #188：回到已通过的separated-return支架路线

## 执行模式与范围

Goal完成模式；用户指定范围N07，父目标`in_progress`、当前连续合格cold start为0/3。新container/epoch；镜像、binary/runtime contract、spawn、wall布局、hover程序、健康/N05门限不变。support scan profile回到`n06_full_airframe_retreat_240_oblique_separated_return`，该路线在#180/#182上支撑过N07完整no-goal hover。此后若通过，#189保持同profile。

## 已有证据与计划

#186的separated-return路线在一次冷启动出现normalized-cost单帧尖峰1.082783；#187 early-view在另一次冷启动触发既有accel-bias 0.15门限。两次均正常安全收尾，无飞行。没有门限变更建议。#180/#182使用同镜像、runtime、spawn、wall layout及separated-return profile，曾完成12/12 support scan、N05三阶段gate和30仿真秒hover；所以#188复用该已成功条件，而不是以改变健康参数获取通过。

## 验收条件

- 初始N05只读拒绝可记录；支持扫描marker必须attached/DISARMED、无truth/control。
- marker后明确等2秒且只运行一次attached N05 online/offline gate；post-release与current-area gates同epoch/map、freshness≤0.4秒。任何健康/准入失败即不发飞行命令，detach、readback、停容器。
- 所有N05汇总项14/14且定位保持有效后，运行30仿真秒no-goal hover；按既有独立误差、EV融合、无GNSS、ULog、ROS graph唯一控制publisher和最终landed/disarmed出口评估。
- 成功为新序列1/3，失败保持0/3；不调门限、不混用旧epoch/map。

## 当前状态

已执行，失败结果详见[#188证据报告](../evidence/n07-preflight-postscan-localization-failure-20261024-188.md)。12/12 support scan和attached N05 online/offline通过；释放阶段helper报fresh DISARMED状态过期，虽然PX4/Gazebo独立读回安全，定位已锁存`telemetry_stale`，故未跑post-release/current-area gates或飞行。N07保持0/3。后续#189计划在ready marker后开始只读全窗口freshness probe，并在释放后优先快速执行N05 gates。
