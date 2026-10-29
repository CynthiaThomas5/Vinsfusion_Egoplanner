# N07.18 #172：bias 越线后的 fresh cold start

## 执行模式与范围

Goal 完成模式；用户指定范围N07，父目标保持`in_progress`。#171在no-goal hover之前的支持扫描中因`accel_bias_norm_exceeded`失败，当前连续合格次数为0/3。

## 假设与唯一主要变量

假设：#171支架返程中的加速度bias越线可能是该独立epoch的间歇性定位失效；#170相同profile的扫描bias最大0.080401并完成12/12。唯一主要变量为新的独立冷启动／epoch。使用与#170/#171相同的固定镜像、runtime、spawn、layout、支架profile、健康配置、N05 gates和hover程序，并保留完整`fixture-vins.jsonl`。

## 判据与完成标准

若#172在相同返程段复现bias超过0.15 m/s²并锁存，视作已有路径相关失效的新判别证据，停止连续悬停验收并回到根因分析，不再盲目重跑；若扫描和released N05 gates通过，则继续原N07全出口。成功须完成12/12支持扫描及安全拆架、attached/released N05 online/offline一致准入、同epoch至少30仿真秒无目标悬停、独立定位／PX4时序评估、ULog EV融合且无GNSS/GPS aiding、ROS graph唯一bridge控制发布者且无真值topic/node，最终landed/disarmed。任何健康门、N05条件和N07验收均不放宽。

## 结果

#172在预设判据下复现失败：新epoch与#171使用相同固定镜像、runtime、wall布局和profile。初始N05 online/offline一致拒绝`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`，未绕过。支架扫描完成7/12阶段，在第7段远端返程平移中，`accel_bias_norm`于sim t=282.680秒首次超过既有0.15 m/s²界（0.150472），峰值0.179247；定位锁存`accel_bias_norm_exceeded`。未进入释放gate或悬停。

与#171一致，bias在先前0.45→0 pitch段已增加：#172阶段6从0.057167升至0.117803，进入阶段7后8.18仿真秒越线；#171也在阶段6抬高后于阶段7越线。相同profile的#165/#167/#168/#170完成且bias未越线；#166/#171/#172在阶段7失败。现有证据把故障定位到支架运动过程中的VINS bias增长，支持“长时间斜视和随后pitch回零的动作序列相关”假设，但未证明底层因果。#172没有复测启动期telemetry freshness。

runner确认支架detach并由Gazebo确认模型已移除；PX4 DISARMED、landed，bridge DISABLED。直接回读亦确认；`bash tools/project.sh stop n07-20261024-172-01`成功，容器exit0，无项目容器残留。未发布导航goal或进入flight。连续合格次数仍为0/3。完整数据见[失败报告](../evidence/n07-support-scan-health-failure-20261024-172.md)。

只读比较发现已有`n06_full_airframe_retreat_240_oblique_separated_return` profile将0.45-rad pitch暴露从约130秒缩至30秒；历史#138 wall和#148 corridor均完成12/12且最大bias分别0.085480与0.076170，但#138的N05 raw-ground拒绝发生在#142相机安装坐标修复之前。下一步#173仅改用该既有profile在当前wall配置重测，其余版本、N05 gate与健康门保持不变。若当前模型下released gate未通过或bias再越线，不飞行并据结果重新评估；N07仍未通过。
