# GOAL C EGO UDP socket drop 与调度 trace #352

- **任务摘要**：延续 #351 的 Fast DDS DataReader listener trace，用只读 `/proc` 采样对齐接收线程 schedstat/state/wchan、EGO进程UDP socket rx_queue/drop计数、RMW wait、publisher和独立reader。
- **用户约束**：沿用项目协作约定；只做 P0–P6 单 D435i 仿真导航范围内的诊断；不改 canonical 源码、QoS、config 或系统设置；最终组合不订阅真值位姿/世界地图，不发布控制。
- **决定**：使用run-local monitor，每约100 ms读取进程线程和socket信息；host `perf_event_paranoid=4`，无可用无密码sudo权限，因此未启用内核trace。保留两端 UDPv4、原QoS和planner-only诊断设置。
- **结果**：domain 218，EGO VPID514、mapping adapter VPID427。2.585827 s pose take空档内adapter发布51帧、独立reader收到52帧且MapStatus epoch/map_id稳定；EGO 705次wait中704次not-ready/unread0、一次ready/unread8，0次successful take。listener在末段报告一次sample_lost，随后data_available unread=5、8。callback TID522为 `dds.udp.61927`，与EGO UDP socket端口一致；调度采样显示2.704 s bracket内runnable wait增加4.013 ms，全部26个gap内thread样本是sleeping。对应socket drop计数从gap前1255增加到gap后1426，其中gap内采样增加154；同一采样点rx_queue均为0。实际 `SO_RCVBUF` 未测。
- **结论边界**：运行队列等待较低，不支持持续CPU starvation；socket drops与sample_lost/take gap同期出现，支持接收侧socket压力为候选，但socket计数不识别topic或样本，不能据此确诊原因。下一步在run-local Fast DDS profile中提高/调整 `receiveBufferSize`，同时读取实际socket buffer并在相同场景复测。
- **待决问题**：participant UDP socket是否受到有效接收缓冲区约束；提升配置是否能改变drop增量、DataReader sample_lost和pose take gap；配置profile是否确实加载。
- **证据**：[报告 #352](../../progress/evidence/p2-ego-pose-rmw-schedstat-trace-20261021-352.json)、[运行清单](../../artifacts/runs/p2-ego-pose-rmw-schedstat-trace-20261021-352/run-manifest.json)、[改动记录](../../progress/changes/2026-10-21-018-p2-ego-udp-socket-drop-trace.md)。
