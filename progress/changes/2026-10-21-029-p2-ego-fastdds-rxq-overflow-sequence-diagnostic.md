# P2 EGO Fast DDS per-sequence socket-drop diagnostic #380–#381

- 任务 ID／日期：029 / 2026-10-21
- 对话摘要：[2026-10-21-029](../../collaboration/dialogues/2026-10-21-029-p2-ego-fastdds-rxq-overflow-sequence-diagnostic.md)
- 修改文件：只在 run-local #381 增加 `recvfrom` ancillary 观测和序号关联分析；新增本证据报告并更新 `CURRENT.md`、证据索引、P2 里程碑引用。未改 canonical source/config。
- 行为变化及原因：#380 发现 Fast DDS 的实际接收入口为 `recvfrom`，因此既有只包装 `recvmsg/recvmmsg` 的探针没有 ancillary 计数。#381 的隔离 LD_PRELOAD 探针改由 `recvmsg` 收取控制消息、剥离探针自己的 `SO_RXQ_OVFL` 项后返回原 payload/source address；应用仍观察 `recvfrom`。新增分析把每个已接收 DATA 序号与其累计 socket-drop 值配对。
- 验证类型：静态、合成 socket 自测、planner-only 仿真运行和离线 trace/RTPS 分析。
- 命令与环境：
  - `bash -n artifacts/runs/p2-ego-fastdds-rxq-overflow-sequence-diagnostic-20261021-381/run-container.sh artifacts/runs/p2-ego-fastdds-rxq-overflow-sequence-diagnostic-20261021-381/analyze-run.sh`
  - `docker run --rm -v "$PWD:/workspace:rw" d435i-vins:dev gcc -std=gnu11 -O2 -fPIC -Wall -Wextra -Werror -shared -o /workspace/artifacts/runs/p2-ego-fastdds-rxq-overflow-sequence-diagnostic-20261021-381/libego_rtps_receive_header_probe.so /workspace/artifacts/runs/p2-ego-fastdds-rxq-overflow-sequence-diagnostic-20261021-381/rtps_receive_header_probe.c -ldl`；同一镜像运行 `python3 /workspace/artifacts/runs/p2-ego-fastdds-rxq-overflow-sequence-diagnostic-20261021-381/test_rtps_receive_header_probe.py`。
  - `bash artifacts/runs/p2-ego-fastdds-rxq-overflow-sequence-diagnostic-20261021-381/run-container.sh`（exit 0）；容器安装 `babeltrace2` 后执行同目录 `analyze-run.sh`；另运行 `analyze_acknack_gap.py` 与 `analyze_rxq_sequence_correlation.py`。
  - `python3 tools/project_status.py`（结构检查 PASS）；`git diff --check` 与 `git diff --cached --check` 均通过。
- 结果及证据位置：探针自测5000包送出、9包在压力后收到，marker的累计丢弃值4991，应用侧无 ancillary 暴露及 `MSG_CTRUNC`。#381 的2.560310 s successful-take gap有48条目标writer `recvfrom` DATA记录，48条都带累计值748–807。ACKNACK请求362/390/397；三条首发DATA均在loopback可见、readerEntityId为0x00000000，但ACKNACK前没有EGO recvfrom回执；精确reader重传晚5.117/5.158/5.193 ms后才返回。序号397邻接的回执计数为781/793，socket样本在首发捕获后2.333 ms从781升至791。只读socket drop括号734→807（+73），仍不能逐包归因。#380 root manifest SHA-256 `b48055ad458bc7949205c23b68bf476add20755a898d5feba203e5690582e4d0`；#381 root manifest SHA-256 `938a43f91af7b2103486bb834066504ad6f36601e3fd03ffa0c83e6fc91671d7`；#381 160项文件清单校验无哈希/尺寸不一致。详细数值与边界见 [证据报告](../evidence/p2-ego-fastdds-rxq-overflow-sequence-diagnostic-20261021-380-381.json)。
- 未验证与 PROVISIONAL：`SO_RXQ_OVFL` 是整个UDP socket的累计值，不能把73次丢弃分配给特定RTPS序号，也不能证明序号397最初未到达是 socket queue drop。`rmw-wait-summary` 的 `seq_contiguous=false`，故对应 analyzer 返回1；其他 base analyzers返回0。eBPF/perf缺少 CAP_BPF/CAP_PERFMON。本诊断不授予 P2/GOAL C 阶段退出或导航净空验收。
- 下一步：继续把序号397的原始/重传 DATA 与接收stage和socket累计值分开核对；保持canonical QoS、socket buffer和freshness gate不变，直到首份DATA缺失的边界可归因。
