# N07.14 #168：连续悬停序列第 2/3 次复现

## 执行模式与范围

Goal 完成模式，用户指定 N07。#167 已取得连续序列第1次。本轮维持相同镜像、runtime、spawn、wall场景、profile、N05与健康门限、EKF2参数、控制行为及30秒no-goal hover程序，只启动独立fresh cold start。

## 结果

Run `n07-20261024-168-01` 完成12/12全机支架路线。attached/released N05五阶段 gate 均online/offline一致接受且epoch/map相同。fixture runner 报告 `localization changed or became invalid during physical scan`，原样保留；fixture已脱架并由Gazebo服务确认移除、fresh LandDetected=true、PX4状态全DISARMED，N05独立summary诊断通过。

同一epoch no-goal hover PASS：30.0仿真秒／39.086墙钟秒，无goal、无clock regression，782/782定位状态有效、301/301 PX4时间域样本有效，最终landed/disarmed。N07 evaluator 11/11 checks通过。ULog通过：54/54空中样本EV位置／yaw／速度／高度融合，GNSS/GPS aiding均未激活；ROS graph三个快照通过唯一bridge控制publisher与无truth ROS topic/node检查。误差为描述性指标，N07未定义数值门限。容器停止退出码0。

完整指标和哈希见[N07 #168证据](../evidence/n07-no-goal-hover-20261024-168.md)。当前连续计数2/3；下一子项#169按同一设置fresh cold start，成功后N07达到3/3。
