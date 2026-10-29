# N07 #192 对话摘要：无额外 freshness probe 的 cold start

## 约束

- 继续用户授权的 N07 Goal 完成模式，目标仍是 3 次连续独立冷启动完整通过。
- 固定镜像、runtime、控制与健康/N05 门限、spawn、布局、support profile、30秒 no-goal hover、独立评估器不变。
- 唯一变量：不运行可选 full-window VIO freshness probe；必需 truth/alignment/bridge 记录继续，graph recorder 仍在 ACTIVE+armed 后启动。

## 证据与判定

#191 N05 14/14 通过，hover 在 2.64 仿真秒因 PX4 local-position/attitude source-age 超前映射时钟 136/144ms、超过既有65ms future-age门而安全降落。假设额外probe负载可能相关，但未证实。#192 关闭probe，只按原 N07 evaluator、ULog、graph 和 landed/disarmed 条件判定；任何失败均不增加连续通过数。

## 结果

#192通过一轮：N05 14/14、12/12 support scan，30秒 no-goal hover，独立evaluator 11/11（在保留raw的phase-transition projection上），PX4 ULog 12/12，ROS graph三快照唯一bridge publisher/no-truth，最终landed/disarmed，容器Exited(0)。本轮计数1/3。

#191的65ms future-age fail-closed未复现；当前结果只说明与“可选probe负载可能相关”一致，不能证明因果。原始记录、evaluator报错和可复算phase转换均保留。下一步#193相同条件新冷启动重复，不运行可选probe，不更改flight阈值。
