# N07 #194 对话摘要：capture 自身 DDS discovery 有界等待

## 已知证据

#193 的 no-goal hover 30 秒、N05 14/14、ULog 12/12 和最终 landed/disarmed 通过；graph 首快照在 capture recorder 自身 discovery 完成前报告 bridge status=null、四个 topic publisher count 为 0，后两张快照识别唯一 bridge publisher。strict N07 evaluator 10/11，连续数 0/3。

## 约束与本轮变量

- Goal 完成模式，用户指定 N07；#194 为全新独立 cold start。
- 保持 image/runtime/spawn/layout/support profile、N05/health/control 阈值、30 秒 no-goal hover 及 no-probe 只读 observer set。
- 唯一变量是 run-local 只读 capture 脚本：自身发现 ACTIVE+armed 状态及四个唯一 bridge 控制 publisher 前不采首快照，最多等待 5 秒；超时保留失败快照。
- 外层 active waiter、flight/evaluator 源码和所有验收标准不改。


## 运行结果

#194满足N07单次出口，streak为1/3：N05 14/14、30.0秒no-goal hover、PX4 ULog 12/12、unmodified evaluator 11/11、ROS graph 3/3 snapshots及final landed/disarmed均通过。support helper的fresh DISARMED状态错误保留，但12/12阶段完成、fixture removal和独立current-area online/offline gate通过。报告：[n07-no-goal-hover-20261024-194.md](../../progress/evidence/n07-no-goal-hover-20261024-194.md)。

graph快照的实际顺序是`airborne_active`、`active_discovery_ready`、`flight_result_written`。第一张已满足唯一bridge/no-truth检查；capture元数据对“首快照”标签的命名不对应快照数组首项。故本轮验收按实际graph数据通过，但不把通过归因于等待门。#195修正run-local recorder：任何snapshot都必须先等待自身DDS view发现ACTIVE+armed和四个唯一bridge publisher，最多5秒；失败时保存timeout快照。其余flight、N05、observer集合和阈值保持固定。

N05 ground-boundary gate是未武装的起降/入口准入证据，HOLD没有subground排除；本轮没有地下飞行，也没有将地下体素空间解释为可飞区域。
