# P2 EGO pose reader RMW trace 诊断

日期：2026-10-17。对话摘要：[2026-10-17-014-p2-ego-reader-delivery-trace.md](../../collaboration/dialogues/2026-10-17-014-p2-ego-reader-delivery-trace.md)。

- 范围：在 patch 0016（pose reader history=100）诊断 overlay 上复跑相同健康输入 harness；未修改自维护或第三方源码、参数、补丁和 PX4 控制路径。#43 收集发布／take 事件，#44 增加 ROS callback 与 executor tracepoint。
- #43：健康60.026秒窗口，depth READY、localization TRACKING、553组配对、31条窗口内 timeout，另6条窗口后。trace 内 adapter 发布和 EGO take 对 depth、pose 各690条一一匹配；pose publish→EGO RMW take 的 P95/最大延迟为0.143/1.324秒（19条超过0.4秒），depth最大24.2 ms。trace未报告丢事件。
- #44：健康60.038秒窗口，493组配对、90条窗口内 timeout、7条窗口后。trace内发布与EGO take对两输入各630条一一匹配；pose P95/最大延迟为0.946/3.001秒（45条超过0.4秒），depth最大24.8 ms。两个主要间断组各有15/23条 pose 在timeout后成批被取，延迟最大1.990/2.358秒。trace未报告丢事件。
- callback/end 与 executor wait trace 未发现长 callback（最大16.7 ms）或大于90.4 ms的 wait；这不能判定 pose subscription 是否已ready但未被executor选取，也不能观察 DDS reader 内部可用状态。证据将症状收窄至EGO侧pose consumption延迟，尚未区分 DDS 通知／availability、executor ready-entity选择或其他RMW路径原因。
- 决定：patch 0016 继续作为可选诊断补丁，不作为修复。history=100、0.4秒 timeout、`ground_height=-0.15 m` 均不获正式接受；保持 P2 未通过。多线程实验先决条件仍是保护 EGO depth/pose callback、GridMap timer 与 reset 的共享状态。
- 原始文件与trace stream见各 run 目录；完整文件哈希清单：#43 [run-artifact-manifest.json](../../artifacts/runs/p2-ego-map-pose-history100-20261017-43/run-artifact-manifest.json)，#44 [run-artifact-manifest.json](../../artifacts/runs/p2-ego-map-pose-history100-callback-trace-20261017-44/run-artifact-manifest.json)。轻量结论见[pose reader trace evidence](../evidence/p2-ego-reader-delivery-trace.json)。
- 验证：#43/#44 probe 均 exit 0；两个 harness `bash -n` 通过；三个 trace analyzer 通过内存语法编译；证据、阶段状态和 trace JSON 均可解析；两份 artifact manifest 共84个文件逐项 SHA-256／大小校验通过。`python3 tools/project_status.py` 报 PASS（仅结构／设计检查）；`git diff --check` 与 `git diff --cached --check` 均通过。最终 status 显示本轮仅修改进度／证据文档并新增 #014 摘要；没有 stage、commit 或 push。进程审计无运行中的仿真、VINS、EGO、mapping 或 probe；仅保留既有 defunct VINS 子进程。
- 局限：单次60秒观察，trace可能扰动时序；容器 `lttng list -k` 报 kernel tracer unavailable，宿主 `perf sched:sched_switch` 又受 `/sys/kernel/tracing` 权限限制，故未采到调度器状态。Fast DDS reader rejection/availability、目标规划、故障注入、PX4、飞行或正式验收均未测。
