# N07.13 #167：重启连续悬停资格序列

## 执行模式与范围

Goal 完成模式，用户指定 N07。#166 已按出口规则将连续序列重置为0/3；本轮复用 #165 的固定镜像、runtime、spawn、wall 场景、12阶段全机支架 profile、N05门限、EKF2设置和30秒 no-goal hover程序。不改健康阈值、控制行为或地面规则。

## 结果

Run `n07-20261024-167-01` 以fresh epoch完成全机支架路线12/12。初始 N05 gate因机体包络内 raw unknown fail-closed；支架扫描后 attached/released N05 五阶段 gate均 online/offline一致接受，epoch/map_id相同，released reason为`all_entry_phases_known_and_clear`。fixture runner错误 `fresh DISARMED status is required for every fixture command` 原样保留；fixture已脱离并确认场景不存在，fresh LandDetected=true，PX4状态样本全DISARMED。`n05-run-summary`独立诊断检查全部通过。

同一epoch无目标 hover程序PASS：30.0仿真秒／38.894墙钟秒、无navigation goal、无clock regression、778/778定位状态有效、299/299PX4时间域有效，真实 landed/disarmed。N07 evaluator 11/11 checks通过。ULog通过；54个空中样本EV position/yaw/velocity/height均融合，GNSS/GPS aiding均未激活，最终落地上锁。ROS graph三个时点均通过唯一bridge控制发布者与无真值ROS topic/node检查。独立VINS、PX4 local与Gazebo只读真值误差为描述性记录，N07没有数值门限。容器停止退出码0。

完整指标和哈希见[N07 #167证据](../evidence/n07-no-goal-hover-20261024-167.md)。N07连续悬停计数更新为1/3；下一子项#168按相同设置fresh cold start，成功后计2/3。
