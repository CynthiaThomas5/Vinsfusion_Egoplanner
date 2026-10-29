# N07 #185 对话摘要：返回段代价尖峰后的冷启动

## 用户约束

- 用户已授权继续完成N07 Goal；要求三次连续cold-start验收。
- 地下不是飞行空间；保持N05／健康门限。定位或准入拒绝即禁止起飞并安全收尾。

## 执行计划

#184新epoch在支架返回段捕获到单帧VINS cost超过既有1.0门限，按`normalized_cost_exceeded` fail-closed。无ready marker或飞行，helper与独立读回确认fixture已移除、PX4 disarmed/landed，容器正常停止，计数0/3。#185保持同一镜像、runtime、spawn、布局、支架profile和门限，仅启动新cold start继续N07重复资格；marker后按既有单次2秒attached gate流程。

计划见[执行记录](../../progress/changes/2026-10-24-185-n07-retry-after-cost-spike.md)，#184数据见[失败报告](../../progress/evidence/n07-preflight-localization-failure-20261024-184.md)。
