# N07 #195 对话摘要：第二次连续 no-goal hover

## 已知证据

#194通过N07单次出口，streak为1/3：N05 14/14、30秒 no-goal hover、ULog12/12、原evaluator11/11、graph三快照和最终landed/disarmed均通过。它的capture metadata首快照标签与实际snapshot顺序不同；每张快照自身的graph断言均通过。当前证据：[报告](../../progress/evidence/n07-no-goal-hover-20261024-194.md)。

## 本轮约束与唯一调整

- Goal完成模式，用户指定范围N07；进行第二个独立cold start。
- 固定镜像/runtime/spawn/layout/support profile、N05/health/control门限、30秒hover、只读observer集合和evaluator。
- 不运行optional freshness probe。
- 仅修正run-local read-only capture顺序：在capture自身DDS view满足ACTIVE+armed及四个唯一bridge control publisher前，不采任何graph snapshot；5秒timeout仍留存failed snapshot。
- N05 current-area fresh gate未通过时不启飞；飞行结束确认安全后停止项目容器。


## 运行结果

#195通过，N07 streak为2/3。N05 12阶段和14项摘要通过，post-release/current-area online/offline gate接受；支架helper在profile结束、fixture removed后报健康收尾错误，trace没有invalid row且fresh gate重新通过，原错误保留。30秒no-goal hover、ULog12/12、evaluator11/11、graph三快照全部通过，最终landed/disarmed并Exited(0)。证据：[n07-no-goal-hover-20261024-195.md](../../progress/evidence/n07-no-goal-hover-20261024-195.md)。

本次gate先于任何capture snapshot就绪，首项`active_discovery_ready`与元数据顺序一致。#196在相同fixed conditions及该run-local gate下执行最后一个独立cold start；任何验收失败都将连续数清零。
