# N10.3/#391 综合校准重试结果

对话摘要：[用户确定的顺序、复用与门限边界](../../collaboration/dialogues/2026-10-27-391-n10-integrated-calibration-retry.md)。

## 本轮目标与改动

按 N10.3 校准协议，用 #391 同一 SITL 运行复用 16 m/4 s native dwell/动态箱体/60 仿真秒 hold，复算到达、raw VIO、跟踪、真实净空、地图查询、资源和故障终态。新增轻量结果报告并把当前执行状态改为反映运行失败及仍活动的容器：

- [N10.3/#391 报告](../evidence/n10-integrated-calibration-result-20261027-391.md) 汇总测量、原始证据路径、失败时间线、当前 PX4/bridge 状态及恢复条件。
- [N10 执行计划](../../docs/n10-completion-plan.md)、[CURRENT](../CURRENT.md) 和 progress/milestones.json 更新到 #391 的实际结果；N10 维持 in_progress、next_goal=N10。未改 GOAL 阈值、次数、N15/N16 顺序或运行时门。
- 原始 run artifacts 未改写。#391 contract SHA-256 为 86debc3c5817dc311b9d929ec6669812d4d69a9bef069a6fa65a58903aaeee01；报告的离线分析引用原 JSON/日志。

## 结果摘要

目标段位置/yaw 联合驻留量测为 3.980 仿真秒，独立达到既定驻留长度；目标动作中跟踪误差 P95 0.6225 m，4 ms 求解器状态全覆盖的离散全机净空最小 0.10604 m。目标完成后的 hold 才发生大漂移：49.304 仿真秒内位置误差 P95/max 8.312/8.349 m，目标后 7.468 s 离开 0.30 m 球。Wall_1 包络余量在 271.072 s 变为 0，273.228 s rotor_0 真实接触，之后 273.444 s 定位适配器锁存 propagated_invalid_quaternion，再触发 EGO depth/odom timeout 和 PX4 NAV_LAND。

PX4 随后保持 failsafe AUTO_LAND，没有到达 landed/disarmed；bridge 为 LANDING、armed、control enabled。SITL 容器仍在运行。按项目停止条件，未对它发 stop、强制 disarm 或启动新运行。因此：本轮运行结果为失败，故障退出证据缺少安全终态；N10.3 及 N10 不通过。

## 验证与限制

运行前工具身份、runtime contract 与 run-local observers 冻结记录见 n10-tool-freeze-used.json。读取器和离线分析报告覆盖完整 4 ms 到达段及 49.088 s 的保持/接触前区间；sampled/discrete clearance 不能视为连续时间证明。map-query 因响应 radius 未序列化仍 INCOMPLETE；资源记录为 193.6 wall 秒的部分样本；均不作通过结论。

本轮没有停掉仍 armed 的控制链。待原生终态或用户对一次性 SITL 紧急关闭给出明确授权后，先关结本次会话，再定位并修复故障响应/漂移问题、补齐 query 采集、继续 N10.3。正式 N15/N16 任务仍留在 N10 冻结后。
