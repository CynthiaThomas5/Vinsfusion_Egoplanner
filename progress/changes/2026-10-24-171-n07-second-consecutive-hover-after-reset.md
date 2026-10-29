# N07.17 #171：新连续悬停序列第 2/3 次

## 执行模式与范围

Goal 完成模式；用户指定N07。#169失败后重置序列，#170为当前1/3。本项继续完整N07 qualification，父目标保持`in_progress`。

## 计划与唯一变量

沿用#170的固定镜像、runtime、spawn、wall layout、全机支架route、N05 online/offline gate、健康门、EKF2参数及30秒 no-goal hover程序。唯一主要变化是独立cold-start epoch。#170初始45秒时序窗口内telemetry健康，且支持扫描、释放gate与悬停均通过；没有证据支持修改健康阈值。继续保持门限和控制行为不变。

## 完成标准

12/12支架扫描并安全拆除；attached/released N05五阶段online/offline一致接受、identity连续且释放后pose在预算内；≥30仿真秒no-goal hover；独立误差、连续定位和PX4时域健康；ULog EV融合与无GNSS/GPS aiding；ROS graph唯一控制发布者且无真值topic/node；最终landed/disarmed。失败则依据连续规则重新计数，N07仍保持未完成。

## 结果

#171未取得N07悬停资格。新epoch启动期45墙钟秒探针中，localization于wall 2.761秒进入TRACKING；telemetry最大源龄0.080秒、source gap P95 0.068秒，未见`telemetry_stale`。初始N05只读门按既有规则拒绝`ground_plane_insufficient_raw_occupied_voxels`，未绕过。

支架扫描完成7/12阶段后中止于第7段返程平移。`fixture-vins.jsonl`显示`accel_bias_norm`于sim t=277.300秒首次超过health配置既有0.15 m/s²界（0.150982），随后升至0.189144；adapter终态`accel_bias_norm_exceeded`。不把此运行归因于telemetry freshness，也未更改门限。相同路线的#170完成12/12且扫描记录最大bias为0.080401；现有证据显示跨epoch结果不同，尚不能判定bias升高的上游原因。

未生成return-pose marker，未进入attached/released N05 gate、无目标悬停或飞行。清理回执确认fixture已detach并由Gazebo确认移除；PX4最终DISARMED、landed，bridge为DISABLED。运行中直接只读回读亦为DISABLED/unarmed/landed。按`bash tools/project.sh stop n07-20261024-171-01`停止，容器exit0；没有项目容器残留。连续计数从#170的1/3重置为0/3，N07保持`in_progress`。详见[失败证据](../evidence/n07-support-scan-health-failure-20261024-171.md)。下一子项#172使用同一镜像、runtime、路径和门限，fresh cold start复核bias越线是否复现；全程保留原健康门。
