# N07.25 #179：第三次连续无目标悬停冷启动

## 执行模式与范围

Goal 完成模式；用户指定范围 N07。父目标保持 in_progress，当前连续合格冷启动为 2/3。仅重复当前固定版本的 N05 支架准入、EKF2 EV 融合和 no-goal hover 出口；不改源码、参数、阈值、门控语义或验收标准。

## 已有基础与缺口

#177 与 #178 为相同固定组合下两个独立 cold start，分别完成 attached/post-release/current-area N05 online/offline gate、30 仿真秒 no-goal hover、独立误差、PX4 ULog 与唯一控制者图检查。需再取得一个不间断的独立通过 run。#178 helper 的定位状态错误保留在报告中；采样 VINS、N05 汇总、gate、hover 与最终证据通过。

## 固定条件与完成标准

- 固定镜像 SHA-256 `099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`、runtime contract SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、spawn `(-6.5,0,0.3,0,0,0)`、`wall_box_column` 与 `n06_full_airframe_retreat_240_oblique_separated_return`。
- 新 container/run/epoch；N05 gate 或定位前置不 fresh 时 fail-closed，不解锁。
- attached、post-release、current-area online/offline gate fresh 同 epoch/map 通过；12/12 支架阶段、脱离、fixture 缺失、final landed/disarmed 有证据。
- 至少 30 仿真秒 no-goal hover；完整独立定位/保持误差、时序、PX4 EV/GNSS/ULog、ROS graph 唯一 bridge publisher 与最终 landed/disarmed 证据。
- 若全部通过，连续计数为 3/3。失败则依固定规则重置计数；不修改任何阈值。

## 结果

#179 未通过 N07：attached N05 live check 因 map source/fusion/snapshot age 超过原 0.4 s 门限而 fail-closed。没有解锁或飞行。fixture 已安全释放、确认 DISARMED/landed 和模型缺失；后续一次 post-release gate 在同 epoch/map fresh 接受，但不替代 attached gate。连续合格计数从2/3重置为0/3。完整证据见[报告](../evidence/n07-preflight-freshness-failure-20261024-179.md)。

## 下一项

N07.26 #180：唯一主要变量为在 `n05-prescan-ready` 后、支架仍 attached 且 PX4 DISARMED 时等待2墙钟秒，再执行原 attached N05 live/offline gate。门限、profile 和其余固定条件不变；gate 仍未接受则立即释放并停止，不起飞。成功后新序列为1/3。
