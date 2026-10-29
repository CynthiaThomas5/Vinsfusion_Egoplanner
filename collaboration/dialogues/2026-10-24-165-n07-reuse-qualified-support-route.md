# N07.11 #165：复用已验证的全机支架观测路线

## 用户约束

- 继续完成 N07；不改变 N05 接受标准、健康阈值或飞控行为。
- 地面以下整格不属于飞行体积，已由审计证据确认并继续采用现有规则。
- 未武装N05检查必须 online/offline 一致；released 五阶段全通过前不得进入悬停。

## 本轮假设与实验

#164在1.8m俯仰返航段触发既有加速度bias门限，未抵达post-scan marker。#146已在同spawn、wall layout和N05相关配置下以 `n06_full_airframe_retreat_240_oblique_early_view` 完成12/12并取得attached/released正向N05 gate。本轮在fresh N07 epoch重用该profile，只改变路线；不将#146 gate直接继承到新run。

## 决策

对新run `n07-20261024-165-01` 使用marker watcher即时执行attached check，释放fixture后复检released gate。门禁满足后再在同一cold start核对EKF2、无GNSS/真值辅助、唯一control publisher，并完成首个≥30仿真秒no-goal hover。任一健康或门禁失败均留证并安全停止；不以结构检查替代实际运行。

## 结果

`n07-20261024-165-01` 12/12支架阶段完成，attached与released N05五阶段在线／离线完全一致接受，same epoch/map_id；所有阶段unknown与occupied为0。支架runner的`outcome=failed`／localization-change报错保留，fixture实际移除，fresh LandDetected=true、DISARMED，released N05门禁接受。

同一epoch首个无目标悬停完成30.0仿真秒，wall39.004s，flight和独立评估均PASS；无navigation goal，定位与PX4时间域连续，真实落地并解除武装。ULog确认EKF2 EV position/yaw/velocity/height全54个airborne samples融合，GPS参数为0且GNSS aiding flags全程未置位；SIM_GZ_EN_ODOM与UXRCE_DDS_SYNCT均为0。独立VINS和保持误差已量化。ROS图空中/落地确认控制由唯一bridge发布者持有、无ROS真值topic/node。

启动期ROS graph快照存在DDS endpoint名称延迟；四个topic各只有一个endpoint，GID与后续确认的bridge publisher完全相同。保留原始快照并以严格的一对一GID连续性作后处理，新增4项单元回归，全部通过。报告见[#165](../../progress/evidence/n07-no-goal-hover-20261024-165.md)。N07为1/3，下一项是fresh冷启动#166，不变更控制/阈值/配置。
