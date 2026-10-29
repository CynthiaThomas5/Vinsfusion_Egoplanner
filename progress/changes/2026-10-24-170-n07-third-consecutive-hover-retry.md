# N07.16 #170：健康前置失败后的新冷启动

## 执行模式与范围

Goal 完成模式；用户指定N07。#169未通过初始N05检查，当前连续合格序列为0/3。本项只重试既有N07完整流程，不更改配置、版本、健康阈值、N05准入门或控制行为。

## 假设与唯一主要变量

假设：#169 的 `telemetry_stale` 是启动期可间歇恢复的输入新鲜性失败，而不是固定配置下每次冷启动必现；同一版本此前 #167/#168 通过、#090失败后也出现过三次通过。主要变量仍是新的独立仿真冷启动／epoch。

维持固定镜像、runtime、spawn、wall layout、支架路线、N05 gates、EKF2 参数和 no-goal hover程序。保留只读时序证据：如初始检查未通过，立即保存 localization status、`/clock`、raw VINS telemetry/odometry、adapted odometry及bridge状态样本；不得据此跳过任何门。先完成12/12支架与attached/released gates，再进行至少30秒无目标悬停。全出口保持原标准。

## 完成标准

完整复现 N07：N05 全机支架与释放后online/offline五阶段门通过；同一epoch ≥30仿真秒 no-goal hover；独立误差、时序健康、ULog EV position/yaw/velocity/height融合且无GNSS/GPS aiding、ROS graph唯一bridge控制publisher且无真值topic/node；最终 landed/disarmed。失败则按规则保持或重置连续计数；不得降低阈值。

## 结果

#170通过，成为新连续序列第1/3次。启动期45墙钟秒只读时序记录未见`telemetry_stale`：localization于wall 2.49秒进入TRACKING，telemetry最大source age 0.168仿真秒。初始N05 gate按原规则拒绝`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；未绕过，后续全机支架12/12完成。

attached与released N05五阶段online/offline一致接受，epoch/map identity连续；释放后pose shift 0.000669m在预算内，N05 summary 14项检查全通过。fixture runner在拆架后的健康receipt复核报告`localization changed or became invalid during physical scan`，错误原样保留；最终结果为全部阶段完成、支架detach与Gazebo移除确认、landed=true、vehicle state全DISARMED。独立安全审计通过，released gate后定位fresh有效。

同epoch无目标悬停PASS：30.0仿真秒／39.020墙钟秒，无navigation action goal、hover position command为0、无clock regression；780/780 hover localization status有效、307/307 PX4时间域样本有效，最终LANDED/disarmed。N07独立评估11/11通过；VINS位置误差RMS/P95/max为0.005015/0.005752/0.005925m，yaw绝对误差RMS/P95/max为0.003661/0.006670/0.008961°；PX4 local hold最大位移0.07645m、Gazebo只读真值最大位移0.07670m，均为描述性指标。ULog 54/54 airborne样本EV位置／yaw／速度／高度融合；GNSS/GPS aiding airborne true样本为0。ROS graph三个快照通过唯一bridge控制publisher与无真值ROS topic/node检查。

容器安全停止，exit0。完整独立证据见[N07 #170](../evidence/n07-no-goal-hover-20261024-170.md)及`artifacts/runs/n07-20261024-170-01/`。当前连续计数1/3；下一子项#171维持同设置fresh cold start。
