# N07 #180 对话摘要：attached gate freshness 时序复核

## 用户约束

- 用户授权 Goal 完成模式，范围 N07，持续至出口通过。
- 地下不属于飞行空间；沿用原 ground-boundary 和 N05 阈值。
- gate 或定位前置失鲜则不解锁；悬停≥30仿真秒，最终landed/disarmed；不更改目标门限。

## 证据与决定

#179 attached gate 因 map source/fusion/snapshot age 超过0.4秒而 fail-closed；没有飞行。支架释放后同 epoch/map 的 post-release gate age恢复为0.108/0.156/0.028秒并接受。#180 只增加 ready marker 后、attached且DISARMED状态下2墙钟秒等待，再运行原attached gate。若失败立即释放并结束；若成功才继续既有流程。详见[执行卡](../../progress/changes/2026-10-24-180-n07-attached-gate-settle.md)。

## 结果

#180 的 attached gate 在实测等待2.000070387秒后 fresh 接受；attached、post-release、current-area online/offline gates 均保持同一 epoch/map，snapshot/source/fusion ages 均低于原0.4秒门限。支架12/12完成、fixture移除与末态 landed/disarmed 均有证据。支架 helper 报 `fresh DISARMED status is required for every fixture command` 并 exit 1，错误保留；N05 summary 14/14 检查通过。

30.0仿真秒 no-goal hover、独立 evaluator 11/11、PX4 ULog 12/12、ROS graph 三快照与 landed/disarmed 检查通过。该次作为失败后重置序列1/3。两秒等待结果支持但不能证明 freshness 时序假设，下一轮 #181 保持该条件做新 cold start。报告见[证据](../../progress/evidence/n07-no-goal-hover-20261024-180.md)。
