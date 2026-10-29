# N07.10 #164：自动化 post-scan gate 时序

## 目标

继续 Goal N07。#163 的9阶段路线已完成；health history记录到 `telemetry_stale` 锁存，attached N05 checker在等待120s后仍没有 optimized odometry，因而没有post-scan快照或released gate结果。用户限定的地下边界仍不变：whole-cell完全低于fresh raw-ground plane的体素在接触阶段排除，地面平面及其上的未知空间按现有规则处理。

## 假设与执行

假设：home marker出现后人工检查调度较慢，健康状态在检查完成前过期。复用#163相同run profile与所有阈值，使用主机marker-watcher立即触发attached N05 checker（20秒上限），随后释放fixture、确认detached/scene absent/fresh landed并立即检查released N05，保存online/offline对照。去掉keep-all ROS状态订阅，避免额外DDS负载。

released五阶段必须全通过才可继续同一冷启动做N07悬停；任何拒绝或失效都保持DISABLED/DISARMED并结束该run。N05、健康门、飞控和控制输出均不改变。

## 结果与决定

Run `n07-20261024-164-01` 复用了相同profile。初始N05 online/offline一致拒绝，地面审计显示0个接触未知中心位于地面以下、另有44个整格地下单元已排除。支架在返航stage 5首次触发既有 `accel_bias_norm_exceeded`，共完成5/9阶段，未到marker；自动检查没有启动。支架移除并确认、PX4 DISARMED、bridge DISABLED、LandDetected=true、容器退出0，无飞行。具体统计见[#164结果](../../progress/evidence/n07-retreat-observation-20261024-164.md)。

当前主要可行动作为复用#146在相同spawn/layout及相同N05相关配置上已完整跑通的 `n06_full_airframe_retreat_240_oblique_early_view`，不再重复失败的1.8m俯仰返航路线。#165保持其他配置／门限不变，在prescan marker即时执行attached gate，确认释放后执行released gate；只有released五阶段online/offline一致全通过才允许同epoch的N07飞行检查。
