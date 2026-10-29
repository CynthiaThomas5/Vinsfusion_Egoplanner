# N07 #170 冷启动重试

## 用户约束

- 用户已授权继续Goal完成模式，范围N07。
- 不降低健康门、N05准入或N07验收条件；每次失败按连续三次规则重算。
- N06 ground-boundary语义已完成；N07 当前阻塞在新epoch启动后 localization `telemetry_stale`、N05无法取得有效optimized odometry。

## 已确认

- #167/#168在相同profile下连续通过2/3；#169未进入支架／飞行，localization失效且PX4保持DISABLED、unarmed、landed，容器exit0，当前序列0/3。
- `Health` 的失效状态锁存；raw VINS后续继续发布不能恢复当前adapter epoch。
- #090曾有类似初始cold-start失败，后续fresh epoch能通过，但不构成#169根因结论。

## 本项决定

#170复用完全相同版本、runtime、支架路线、门限与hover程序，以独立cold-start epoch重试。若前置检查失败，保留同时段clock、telemetry、raw／adapted odometry与health状态，用于判断同一故障是否可复现；只有N05 gate全部通过后才运行支架与后续hover。完成后按证据更新计数与N07状态。

## 结果

#170通过并计为新连续序列第1/3次。启动期45秒记录无telemetry stale；initial N05依旧按`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`拒绝，未绕过。支架12/12完成，attached/released N05均online/offline一致接受且identity不变，summary诊断通过。fixture runner health receipt error保留，然而支架已detached／移除、landed、DISARMED，释放门通过。之后30秒no-goal hover、11/11独立评估、ULog融合与GNSS无辅助、ROS graph唯一控制者检查均通过。容器exit0。完整报告见`progress/evidence/n07-no-goal-hover-20261024-170.md`。下一步#171以同设置fresh cold start。
