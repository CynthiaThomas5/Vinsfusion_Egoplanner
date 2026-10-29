# N07.10 #164：自动化 post-scan gate 时序

对话摘要：[自动化 post-scan gate 时序](../../collaboration/dialogues/2026-10-24-164-n07-immediate-postscan-gate.md)

## 父目标与依据

执行模式：Goal 完成模式；用户指定范围 N07。父 N07=`in_progress`，子项 N07.10 #164。#163 原 pitch route 完成9/9，初始 N05 拒绝地面及其上方 unknown；route结束后 `/localization/status` 于 sim=335.152s 锁存 `telemetry_stale`，normalized cost仅0.472924。attached checker没有收到新鲜 optimized odometry，等待120s后失败；post-release地图快照未生成。status事件证明cost越限不是本次锁存原因，但触发时的具体 stream receipt-age 仍未定。

## 假设、变量与判据

假设：#163的attached检查未能在返回home后的短fresh-health窗口内完成；把检查移到marker-watcher中由 `n05-prescan-ready.json` 直接触发，可减少调度延迟并取得可用的post-scan快照。

唯一变量是 gate检查的编排与启动时序。复用#163完全相同的cold start、fixture profile、布局、N05配置、健康门和阈值；不增加keep-all状态订阅。marker一出现立即运行attached检查，使用20s有界等待；之后无论attached gate接受或拒绝均释放fixture，确认detached/scene absent/fresh landed；满足清理前提后立即运行post-release检查并做独立离线重放。指标是取得snapshot、在线/离线逐项一致及五阶段结果。只有post-release五阶段全通过，才在同一epoch核对EKF2 EV融合、无GNSS/真值和唯一控制publisher，再开始≥30仿真秒无目标悬停。

## 执行边界

新run `n07-20261024-164-01`。marker-watcher只调用已有只读N05 checker/evaluator并写本run日志，不发布控制、目标或真值。若scan未完成、checker缺少fresh输入、released gate拒绝或安全清理状态不明，保持DISABLED/DISARMED；按项目流程停止本run，不转入新的epoch续接。无源代码或阈值修改。

## 结果

Run `n07-20261024-164-01` 的初始 fresh N05 online/offline 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；plane z=−0.35m，接触阶段436个未知中心中0个低于地面，另排除了44个整格地下单元。HOLD 566个未知中心均高于地面。

该路线在返航 stage 5 于 sim=202.456s 首次越过既有 accel-bias 上限（0.150866m/s² > 0.15），完成5/9阶段，未到 prescan marker，attached/released checks 均未启动。fixture 已确认移除；LandDetected新鲜且为true、PX4 DISARMED、bridge DISABLED，容器退出0，无飞行。详见[#164报告](../evidence/n07-retreat-observation-20261024-164.md)。

下一项 #165 复用 #146 已完整跑通的 `n06_full_airframe_retreat_240_oblique_early_view` wall 路线，配置、阈值、地面规则保持不变。marker 到达后执行attached检查、释放并执行released五阶段检查；仅在线／离线一致全通过后，才在该冷启动继续核验EKF2与无目标悬停。
