# N07.15 #169：连续悬停序列第 3/3 次复现

## 范围

继续用户指定的N07 Goal。#167和#168已连续通过2/3。#169在相同固定镜像、runtime、spawn、wall layout、支架route、N05门限、定位健康门、EKF2参数和no-goal hover程序下进行第三次fresh cold start；不改阈值或控制行为。

## 判据

完成12/12支架扫描；attached/released N05五阶段online/offline一致通过且epoch/map一致；同一epoch no-goal hover至少30仿真秒，VINS/PX4时间域和健康连续；ULog证实EV融合且GNSS/GPS aiding未激活，ROS graph确认唯一`uav_px4_bridge`控制publisher与无ROS真值topic/node；独立误差可复算，最终真实landed/disarmed。全项通过后连续计数3/3并复核N07状态。

## 结果与决定

#169在初始N05只读检查等待150秒后仍没有有效优化里程计，检查收到的localization状态为`telemetry_stale`；bridge保持DISABLED、未武装且landed。没有启动支架或飞行，容器经项目入口停止并退出0。连续计数从#167/#168的2/3按失败规则重置为0/3。详情见[失败证据](../../progress/evidence/n07-preflight-health-failure-20261024-169.md)。下一步#170仅更换fresh cold-start epoch，维持全部门限与配置；增加低负载只读的VINS telemetry/定位状态时间记录，以便若同一门再次失败时保存触发前后证据。
