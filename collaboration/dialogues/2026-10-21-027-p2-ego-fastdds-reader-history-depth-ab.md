# GOAL C EGO Fast DDS DataReader history depth A/B #372–#377

- **用户指令**：延续完成项目 GOAL 的授权；采用 ponytail 的最小必要改动方式。
- **约束**：P0–P6 单 D435i 仿真；保留工作区已有 staged/unstaged 修改；不伪造实现；本轮不得启动 PX4、发布控制或 goal、订阅 truth/control；实验源码只放 run-local artifacts，不写回 canonical EGO。
- **问题**：确认 EGO DataReader 的有效history深度，并解释多秒pose take gap在链路中的位置。
- **决定**：只在run-local副本做depth25/100 A/B；随后把loopback RTPS头、EGO receive API、Fast DDS reader hooks按sequence对齐。canonical QoS和freshness gate不动。
- **已确认**：depth25/100在同类50样本批次中分别保留25/50条。#372/#375/#377的多秒gap包含迟到的RTPS sequence；首份DATA在loopback捕获可见，却没有对应的EGO `recvfrom`返回记录，约2.4–2.61秒后同序号副本才返回并触发按序listener/history通知。#377的pose/sync计数停在499，源戳年龄从0.495秒增至1.700秒，越过既有0.4秒门。
- **未确认**：首份数据为何在loopback捕获后没有到达EGO receive API。socket drop与队列峰值支持接收侧压力假设，但计数聚合、无法按sequence归因；depth100重放旧样本的建图风险也未评估。
- **阶段状态**：P2保持passed，健康阈值PROVISIONAL，GOAL C pending；不改里程碑。没有PX4、goal、truth/control、PCAP或payload字段。
- **结果链接**：[轻量证据报告](../../progress/evidence/p2-ego-fastdds-reader-history-depth-ab-20261021-372-377.json)、[变更记录](../../progress/changes/2026-10-21-027-p2-ego-fastdds-reader-history-depth-ab.md)、[本次运行清单](../../artifacts/runs/)。
