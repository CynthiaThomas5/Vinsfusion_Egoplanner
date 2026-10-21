# GOAL C EGO RTPS 序号诊断 #366–#368

- **用户指令**：继续完成文件夹中的 GOAL；本轮用户以“继续”延续既有授权。
- **适用约束**：只推进 P0–P6 单 D435i 仿真。旧来源只读；不伪造包或 launch；保护已有 staged/unstaged 文件；本轮只做诊断，不订阅真值、不发布控制、不启动 PX4；RTPS 仅保存字段与 DATA 序号，不保存 PCAP 或应用 payload。完成时维护 CURRENT、证据、变更记录与对话摘要；结构检查不等于阶段通过。
- **问题**：#365 证明有效位姿流可与 EGO 空 reader history 窗口并存，但没有目标 writer RTPS 包的证据。目标是校准 RTPS header/源 GUID 过滤，再将目标 DATA 序号与精确 EGO successful-take gap 对齐。
- **决定**：#366 用可靠 `PoseStamped` publisher/subscriber 校准 exact endpoint 与 GUID 前缀 BPF。#367 首次只在 attempt-002 得到有效数据；#367 attempt-001 因 ROS topic-info 字段次序假设错误而排除并保留。#367 显示 readiness gap 中有目标 DATA 序号，但 TShark 报告丢包且未捕获订阅初始化事件。#368 在 EGO 初始化前短暂跟踪所有 UST 进程，捕获订阅句柄后仅跟踪 EGO 与 mapping adapter；TShark 缓冲设64 MB，显示过滤器仅输出目标 writer DATA 头字段。
- **已确认**：#368 exact successful-take gap 2.365682520 s；adapter `rmw_publish` 46次；loopback 捕获到46个唯一目标 DATA 序号（66–111），观测范围内无缺号。EGO 644次 wait not-ready/history unread=0，随后 ready 读到25条；gap 内状态 matched=1、lost/rejected=0。独立相机位姿流源戳最大间隔66 ms，MapStatus 单一 epoch/map_id。RTPS DATA 的 `ENTITYID_UNKNOWN` 按 OMG DDSI-RTPS v2.5 的 participant 语义解释，目标 UDP 端口从 exact-reader DATA 行推定。
- **未确认**：loopback 捕获点之后的 EGO UDP socket 实际接收、Fast DDS/内核/调度的具体丢失位置，以及无缺号序列是否完整。不得从等量的46次 publish 和46个唯一序号推断逐样本一一对应。
- **阶段状态**：P2 仍 passed，健康阈值 PROVISIONAL；GOAL C 仍 pending。未调整 milestones。下一步用只读内核/socket 接收事件对齐目标端口，避免捕获或保存应用 payload。
- **证据**：[轻量证据报告](../../progress/evidence/p2-ego-rtps-sequence-valid-pose-diagnostic-20261021-366-368.json)、[变更记录](../../progress/changes/2026-10-21-025-p2-ego-rtps-sequence-diagnostic.md)。
