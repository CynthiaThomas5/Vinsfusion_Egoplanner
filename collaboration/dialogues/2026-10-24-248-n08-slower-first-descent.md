# #248 N08 首段下降时长诊断摘要

## 约束

在 #247 负 Y profile 上只把 z=1.0→0.5 m 首段下降从 8 s 延长到 20 s；保留负 Y 观察、planner 与所有阈值。若仍 health-lock，完成安全清理，不进入 compute-only 或 XY。

## 结果

负 Y view/return 完成，首次下降时 `normalized_cost_exceeded`=1.037158，优化与 telemetry 源龄约64/68ms，stale观测为空，prior检查通过。HRT/ROS时间有效，PX4 DISARMED、landed，bridge disabled，fixture移除，容器 exit0。没有post-release same-map gate。

比较 #247/#248，两种下降时长都在约0.8m高度附近越过cost门；继续减慢没有收益。#246不含负 Y追加视角时同高度cost较低，#233的negative-only profile曾完成N05。epoch各自独立，尚无因果结论。

## 下一步

#249 复用现有 `n08_overhead_negative_side_view` negative-only profile，在新鲜run中取图，检验当前负Y hold unknown；不重跑旧map结论、不复测N07、不放宽任何门禁。
