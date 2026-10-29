# N07 #171：新序列第二次冷启动

## 用户约束

- Goal 完成模式，范围N07；持续到N07全部出口通过。
- 保留原N05、健康与N07门限，不把初始 raw unknown 拒绝绕过。
- 仅用 PX4 SITL；不发导航目标，no-goal hover仍按原程序落地上锁。

## 已确认状态

- #169因初始`telemetry_stale`失败，连续数归零；N07上游根因仍未判明。
- #170在新epoch通过：startup时序无telemetry stale，12/12支架与attached/released N05 gate通过，runner teardown receipt error原样保留但安全条件与独立gate通过，30秒no-goal hover和11/11独立评估通过。当前连续序列1/3。

## 本项决定

#171沿用#170完全相同的版本、runtime、路径和门限，仅换新的独立冷启动epoch。按相同N05准入与hover证据链验证；如果失败，停止飞行或按安全状态落地，重新计算连续次数并留存原始结果。

## 结果

#171启动期45秒未见`telemetry_stale`，初始N05仍按原规则拒绝raw ground occupancy不足。支架第7段返程中，VINS `accel_bias_norm`从低值持续上升并于sim t=277.300秒越过既有0.15 m/s²健康界，终态`accel_bias_norm_exceeded`；扫描7/12停止，未进入释放gate或悬停。#170相同路线扫描bias最大0.080401并完成12/12，原因尚未判明。支架已拆除／确认移除，PX4 DISARMED且landed，bridge DISABLED，容器经项目stop流程exit0。连续计数重置为0/3；#170结果保留但不属于当前连续序列。完整证据见`progress/evidence/n07-support-scan-health-failure-20261024-171.md`。下一步#172按原设置fresh cold start，使用扫描内VINS bias时序判定该越线是否复现；不调门限。
