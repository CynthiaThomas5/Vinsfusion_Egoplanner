# P2 EGO first-DATA receive-gap independent repeat #382

- 任务 ID／日期：030 / 2026-10-21
- 对话摘要：[2026-10-21-030](../../collaboration/dialogues/2026-10-21-030-p2-ego-fastdds-rxq-independent-repeat.md)
- 修改文件：创建 run-local #382，基于 #381 的已哈希探针/trace输入，使用 ROS domain 222 与新 Gazebo partition；新增独立 repeat 证据并更新 CURRENT、README、证据索引和 P2 里程碑证据。canonical source/config/QoS/buffer/freshness 均未改。
- 行为变化及原因：复用 `recvfrom`→内部 `recvmsg` 的 run-local探针，把 ACKNACK 所请求序号的首次 loopback DATA、ACKNACK时刻、精确reader重传、EGO recvfrom与SO_RXQ_OVFL邻近值逐条关联；另明确普通序号集合交集会被同区间内重传掩盖。
- 验证类型：C探针静态构建、合成 UDP 队列压力自测、planner-only 仿真、离线 RTPS/trace 分析、run/source manifest 校验。
- 命令与环境：
  - `bash artifacts/runs/p2-ego-fastdds-rxq-overflow-sequence-diagnostic-20261021-382/run-container.sh`（exit 0；capture helper exit 0）。
  - 容器中安装 `babeltrace2` 后执行 `artifacts/runs/p2-ego-fastdds-rxq-overflow-sequence-diagnostic-20261021-382/analyze-run.sh`、`analyze_acknack_gap.py` 与 `analyze_rxq_sequence_correlation.py`。
  - 合成探针5000包压力下收到9包、marker累计值4991，应用未见探针ancillary，`MSG_CTRUNC=0`。结构检查、JSON/manifest校验及 `git diff --check` 通过。
- 结果及证据位置：#382 2.386491 s take gap 内47条目标 DATA `recvfrom`回执均有计数。ACKNACK请求573、603；两个首次 DATA 均在 loopback 可见但 readerEntityId=0x00000000，在ACKNACK前无 EGO recvfrom 回执。精确reader重传分别晚5.133/5.193 ms，随后才出现在 recvfrom。序号573附近计数从相邻回执511升至525，socket采样在首包后0.410 ms为518；序号603附近相邻计数543→547。gap socket丢弃计数511→547（+36），同长前窗+39、后窗0。证据报告：[ #382 ](../evidence/p2-ego-fastdds-rxq-independent-repeat-20261021-382.json)。#382 run manifest SHA-256 `5b2a72af2629bcd01250ee866f8e76aebba2cc36872766bb7a319968b51fb141`，163项文件均验证。
- 未验证与 PROVISIONAL：两轮均把首发 DATA 缺失定位到EGO recvfrom之前；socket队列溢出是合理但未证实的机制。SO_RXQ_OVFL覆盖整个socket，不能给被丢包命名RTPS序号；20 ms采样无法捕捉微突发。eBPF/perf 缺少 `CAP_BPF`/`CAP_PERFMON`。`rmw-wait-summary` 返回1，因为 `seq_contiguous=false`；其余基础分析返回0。本重复不授予GOAL C或P2阶段退出。
- 下一步：精确的内核丢弃归因需要具备权限的逐socket trace；当前环境不可用。保留 QoS/buffer/freshness门不变，继续 GOAL C 的 known-free 路径、密集轨迹/机体包络和多布局验证。
