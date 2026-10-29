# N07.39 #193：同配方第二次独立冷启动

## 模式、基础与缺口

Goal 完成模式，用户指定范围 N07；当前父目标 in_progress，连续合格冷启动 1/3。#192在固定image/runtime、spawn、wall布局和separated-return支架路线下，通过N05 14/14、30秒no-goal hover、ULog 12/12、独立hover evaluator 11/11及graph唯一publisher/no-truth，最终landed/disarmed。可选freshness probe未运行。

## 执行

运行ID：`n07-20261024-193-01`。采用新容器/新SITL/N05身份，其他条件与#192一致：同一镜像和runtime contract、spawn、wall layout、support profile、N05/health/control阈值、30秒no-goal hover、truth/alignment/bridge只读记录器和ACTIVE+armed graph capture；不运行可选VIO freshness probe。对重复phase observer输出继续保留raw timeline，并以已审阅的run-local transition projection作为未修改N07 evaluator输入。

任何N05 14/14、current-area fresh gate、flight precondition或定位/遥测健康不满足时不启用；flight失败则保留fail-closed结果并把连续计数复位。

## 完成标准与范围

原N07 evaluator 11/11、PX4 ULog 12/12、30仿真秒no-goal hover、airborne/landed graph快照中每个PX4控制topic唯一publisher且无truth节点/topic、最终landed/disarmed。通过计数为2/3，并继续#194；失败则0/3。只允许本轮仿真与只读记录/评估，不改源码、配置、飞行控制或门限。

## 产物

运行档案、N05 gates/summary、flight、truth/alignment/bridge、phase-transition provenance、ULog、graph/evaluator与安全停止证据；相应轻量证据报告、变更记录和对话摘要。

## 实际结果

#193 完成新冷启动：初始N05一致拒绝，12/12 support scan，attached/post-release/current-area均接受，summary 14/14。fixture helper错误 `fresh DISARMED status is required for every fixture command` 原样保留；独立检查确认已移除。

No-goal hover PASS，30.0仿真秒，无导航goal；定位/PX4 telemetry稳定，最终landed/disarmed。可选freshness probe未运行。PX4 ULog 12/12；EV/no-GNSS和最终状态通过。graph waiter在ACTIVE+armed触发后，recorder首快照仍看到 `bridge_status=null`、四个控制topic各0 publisher；后续airborne与final快照均每topic唯一`uav_px4_bridge`且无truth节点/topic。strict graph reconcile失败，独立evaluator 10/11，唯一失败为graph owner。

严格三连因此从 #192 的1/3复位为0/3。证据及哈希见[报告](../evidence/n07-graph-snapshot-discovery-failure-20261024-193.md)与JSON。flight/ULog确认落地上锁，Gazebo模型列表确认支架fixture不在场，容器Exited(0)、无活动项目容器。

## 下一步与限制

#193显示graph recorder本身的participant discovery时序有竞争：触发器已看到ACTIVE+armed，而新capture进程首快照仍未发现bridge status/发布端点；同一进程后续快照立即恢复正常。#194固定其余所有条件，只在run-local只读capture进程内增加有界发现等待：在ACTIVE+armed且四个控制topic各有且仅有`uav_px4_bridge` publisher前不采首快照；5秒内未就绪就保留失败快照并退出，不过滤/替换图数据，也不改变验收器。

验证：ULog分析12/12；graph reconcile因首快照0 publisher明确FAIL；N07独立评估10/11；停止命令`bash tools/project.sh stop n07-20261024-193-01`后容器Exited(0)，活动容器数0。
