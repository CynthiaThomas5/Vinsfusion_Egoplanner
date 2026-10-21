# GOAL C EGO DataReader listener trace #351

- **任务摘要**：在 #350 的双端 UDPv4 主数据路径诊断上，对 EGO 实际 camera-pose DataReader 安装透明 listener proxy，直接标记 `on_data_available`、sample-lost/rejected 等回调，并对齐 RMW wait、successful take、publisher 和独立 reader 时间线。
- **用户约束**：沿用项目协作约定；不修改 canonical 源码、QoS 或 config，不把诊断样条当作导航验收，最终组合不订阅真值、不发布控制。
- **决定**：probe 与 listener proxy 只放在 run-local artifacts；安装时保存并转发原 listener 和原 StatusMask。先用 800 条消息的单独 smoke 验证代理，再运行 domain 216 主实验；EGO 与 mapping adapter 继续使用 `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`。
- **结果**：smoke 成功保留非空原 listener，800/800 帧到达、无 gap/invalid，观测到800次 `data_available`。主实验在2.239734 s EGO pose successful-take gap期间，adapter发布44帧、独立reader收到44帧（最大源戳间隔66 ms、MapStatus epoch/map_id稳定）；EGO有609次wait返回，其中608次not-ready且unread=0，另一次ready时unread=10。DataReader listener的587次回调全部为 `data_available`；选中gap内仅有末端3次回调，unread依次为1、10、25，首次发生在下一次successful take前55.625 μs。sample-lost/rejected listener回调为0，状态轮询中两个累计状态均保持0。
- **结论边界**：证据将该窗口定位到 EGO DataReader/participant 接收路径：上游发布和独立reader在同窗持续前进，而 EGO DataReader history 在绝大多数 wait 返回时为空。单次运行不能区分 Fast DDS 传输端点、reader内部和线程调度原因，也不证明 UDPv4 导致该现象。
- **待决问题**：EGO reader为何直到 take gap 末端才收到一批数据；是否为接收线程/participant调度、特定传输端点或其他 Fast DDS reader 行为。
- **证据**：[报告 #351](../../progress/evidence/p2-ego-pose-rmw-listener-event-trace-20261021-351.json)、[运行清单](../../artifacts/runs/p2-ego-pose-rmw-listener-event-trace-20261021-351/run-manifest.json)、[改动记录](../../progress/changes/2026-10-21-017-p2-ego-pose-rmw-listener-trace.md)。
