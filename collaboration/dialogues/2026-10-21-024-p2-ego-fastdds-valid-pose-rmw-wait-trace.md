# GOAL C 有效相机位姿窗口下的 EGO reader 诊断 #362–#365

- **任务摘要**：跟进 #361 的约60 ms propagated future-stamp异常；在有效相机位姿流下查看EGO RMW wait、Fast DDS reader状态和history-latency统计，并校准统计observer。
- **用户约束**：保持单D435i仿真范围；只读诊断，不发goal、不启动控制/PX4、不接真值；保留已有工作区修改；不放宽阈值或改QoS/canonical配置。
- **已确认**：#362观测到的传播戳源龄为−6至+6 ms，未复现超过20 ms future guard；有效位姿流下仍有EGO多秒pose计数停顿。#363（String/BEST_EFFORT）与#364（PoseStamped/RELIABLE）精确端点校准各得到20条history-latency统计样本。#365独立observer收到915条位姿与200条ready MapStatus；最大2.23772 s的EGO take gap期间，adapter仍有47次位姿rmw_publish。EGO匹配保持1、状态lost/rejected为0，611次not-ready wait时reader history为空，末次ready时看到25条积压。wait序号完整，分析器通过。
- **结论边界**：数据到达EGO应用take之间的中断可定位在DataReader history插入/通知之前的观测路径，但没有packet-level writer序号证据，不能断定是丢包、writer history、RTPS传输或Fast DDS内部调度。统计observer经校准，但实际writer-reader pair在#365仍无样本。freshness旁路probe异常退出，连续位姿/MapStatus有效性由独立reader trace确认。
- **未决问题**：mapping writer的RTPS DATA序号在长take gap期间是否到达EGO接收socket；若到达，哪些序号进入reader history、哪些未进入。
- **下一步**：run-local只读解析RTPS头和序号，避免解码或保存应用payload；继续保持20 ms future guard、0.4 s freshness、原QoS与unknown fail-closed。P2 passed状态和GOAL C pending不变。
- **证据**：[汇总报告](../../progress/evidence/p2-ego-fastdds-valid-pose-rmw-wait-trace-20261021-362-365.json)、[改动记录](../../progress/changes/2026-10-21-024-p2-ego-fastdds-valid-pose-rmw-wait-trace.md)、[run manifests #362–#365](../../artifacts/runs/)。
