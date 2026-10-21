# P2 EGO pose publisher / reader 同窗追踪 #346

- **任务**：继续推进 GOAL C 输入回执诊断，判断 EGO pose reader 停滞时 adapter 是否仍转发、同话题独立 reader 是否仍收到。
- **约束**：只在新项目内运行；旧来源只读；单 D435i 仿真；无在线真值、PX4、控制器或轨迹执行；保持 QoS、同步器和 0.4 s 门限不变；不因诊断结果解除 unknown fail-closed。
- **决定**：以独立 ROS domain / Gazebo partition 重跑 #345 场景，复用已校验 EGO overlay，通过 MapStatus forwarded count、独立 PoseStamped 收件和 EGO 内部 message_filters receipt counter 同步对照。首次 overlay 路径 preflight 失败日志保留，修正路径后重新运行。
- **已确认**：52 条 EGO timeout 日志出现两段 pose counter 平台，分别 1.800 s 与 0.700 s 墙钟。两段中 adapter forwarded count 与独立 camera-pose reader 均前进，EGO depth reader 也前进，EGO 内部 pose/sync 不动，RMW message-lost 均为0。具体根因仍未区分 reader readiness/history 与 executor/callback 调度。
- **待确认**：EGO pose reader 低层 RMW readiness 与 DDS sample lost/rejected 状态是否与回调停滞一致；低负载重复能否复现。
- **当前验收状态**：后段获得一条未执行 B-spline；同身份快照比 spline start 晚72 ms。中心线103点里41点仍落在实验例外允许的起点 unknown voxel。此轮仅诊断，GOAL C 保持 pending。
- **记录**：[改动与验证](../../progress/changes/2026-10-21-013-p2-ego-pose-publisher-reader-paired-trace.md)、[轻量证据](../../progress/evidence/p2-ego-pose-publisher-reader-paired-trace-20261021-346.json)、[运行清单](../../artifacts/runs/p2-ego-pose-publisher-reader-paired-trace-20261021-346/run-manifest.json)。
