# N07.21 #175：移除额外流探针的分离返回复核

## 执行模式与范围

Goal 完成模式；用户指定N07，父目标仍`in_progress`。当前合格连续次数0/3。#174在`oblique_separated_return`的pitch转入期间出现孤立normalized-cost尖峰，但raw源时间戳新鲜；#173同profile完整12/12后则因`telemetry_stale`未能准入N05 gate。

## 假设与唯一主要变量

假设：额外高频VIO只读probe可能改变仿真负载或时序，但#174与#173求解耗时相近，尚无因果证据。主要变量是是否启用该额外probe。#175移除额外probe，保留支架runner内置的VINS telemetry、odometry和健康记录；固定镜像、runtime、spawn、world、layout、profile、健康门、N05门及N07 hover程序不变。

## 完成标准

同epoch完成完整12/12支架、安全detach/移除与fresh attached/released N05 online/offline一致准入；只有以上准入通过，才执行至少30仿真秒no-goal hover并完成独立误差、PX4 EV融合／无GNSS、ROS graph唯一控制者／无truth、landed/disarmed验证。任何健康锁存、缺少fresh odometry或N05拒绝均不解锁、不飞，安全收尾后保留失败证据；不改阈值。

## 结果

#175完成分离返回路线12/12阶段，normalized-cost峰值0.835579、accel-bias峰值0.095803m/s²，均未越现有健康门。初始N05按raw unknown拒绝；attached online/offline fresh gate随后一致接受。fixture在detach/remove后因最后的fresh DISARMED status缺失而报告runner failed；attachment记录含detached、scene确认模型不存在。独立readback确认PX4 DISARMED、landed，bridge DISABLED、armed/control_enabled=false；项目stop后容器Exited(0)。

post-release N05只读check超时missing odom，收到bridge/clock/localization/map。localization随后锁存telemetry_stale，status source stamp 435.304s、clock 606.676s；更晚raw VINS telemetry/odometry单次readback已更新到约620.272/620.932s，optimized odom仍无输出。无release gate准入、飞行或hover，计数仍0/3。#175显示无额外probe的本次pitch代价峰值低于#174，但不足以证明probe是因果变量；支架原生记录另有约2.772s gap，无法确认adapter是否接收到了相同gap。详情见[证据报告](../evidence/n07-support-scan-attached-pass-release-stale-20261024-175.md)。

下一项#176保持同profile和门限，不在支架扫描期间运行额外probe；仅在attached N05 online/offline fresh接受后、fixture release前启动只读source/adapted odom时序probe，捕获release至post-release gate的首个断点。gate未通过仍不飞；gate通过后停止probe并在同epoch执行no-goal hover。
