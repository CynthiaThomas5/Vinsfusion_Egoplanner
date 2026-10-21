# P2 EGO filter callback receipt diagnostic #291

用户要求继续推进 `GOAL.md`。本轮使用 Jazzy 隔离构建；不修改 `src/vendor`、不改变 canonical patch 顺序、健康门或阈值，不启动控制器/PX4，不订阅真值。

## 本轮决定

- 在 #289 run-local unknown-as-obstacle 源码副本上依序应用已有诊断 patch `0012→0013→0015`：增加调度上下文、计数 EGO 既有 message_filters pose/depth subscriber 的输入回调与 RMW message-lost 事件。
- 继续运行低带宽独立 camera-pose observer，对准上一轮 EGO 输入超时问题；本轮换用独立 `ROS_DOMAIN_ID=138` 和 Gazebo partition。
- 不将 B-spline 生成解释成轨迹执行或避障通过。由于现有 receipt counter 只附在 timeout warning，本轮没有 timeout 时不能声称已测得内部 filter 频率。

## 已确认结果

- 隔离源码副本 dry-run/patch 顺序通过，EGO 五包 fresh build 5/5通过；新 `ego_planner_node` SHA-256 为 `f884323c…620b00`，`libplan_env.so` 为 `58e59c48…8d9dc`。canonical vendor 源码与 `dependencies/sources.json` 未改。
- 约70秒观测窗未复现 EGO `odom or depth lost`，所以 patch 0015 的 timeout 计数没有日志样本，根因仍未定位。
- 独立 pose observer 收到1,204条 PoseStamped、70条心跳，源戳单调递增、最大源时间间隔66 ms，observer干净退出。
- 目标探针捕获120条未执行 spline；定位最终因 `normalized_cost_exceeded` 关闭 mapping gate。无控制节点/话题和真值输入。
- 与 #290 的重要差异：#290 启动脚本误复用 #289 的 ROS domain 136 与 Gazebo partition，虽顺序运行且启动前没有项目容器/节点，但并非独立 domain。#291 用新的 domain/partition 未复现 timeout。域复用、run间变异与诊断 overlay 三者未隔离，不能归因。

## 待决问题

- 在正常运行但没有 timeout 时，需要让既有 filter callback 计数周期性输出，才能直接比较 EGO pose/depth 两端与同步器计数。
- 需要独立重复检验 #290 的输入 timeout 是否受 domain 环境或随机运行差异影响。
- GOAL C 地图 free/unknown、覆盖、长期运行仍未验收；P2通过不代表 P6 或 A–H完成。

证据：[轻量报告](../../progress/evidence/p2-ego-filter-callback-receipt-20261020-291.json)；运行原始数据在 `artifacts/runs/p2-ego-filter-callback-receipt-20261020-291/`。
