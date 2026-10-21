# GOAL C EGO pose reader UDPv4 diagnostic #349–#350

- **任务摘要**：继续调查 EGO camera-pose take gap；对照同一诊断基线，将 EGO 与 mapping adapter 的 Fast DDS 内建传输设为 UDPv4。
- **用户约束**：旧部署和 ROS_SEARCH 只读；保护现有未提交修改；本轮只做 P2/GOAL C 诊断，不把单次运行或结构检查视作地图/避障验收；最终链路不能接入真值，控制仍由 PX4 bridge 独占。
- **决定**：保持 #348 的 EGO binary、RMW probe、QoS、0.4 s timeout、0.5 m diagnostic inflation 和 planner-only运行组合；#349 的 EGO-only UDP尝试若mapping gate未ready则排除，不作因果比较。
- **结果**：#349 adapter未确认 `plan_env cleared`，camera-pose observer为0帧，goal probe在ready前超时，标为排除。#350 两端UDPv4后mapping ready；2.614472 s take gap内publisher与独立reader各观察51帧，EGO 708次not-ready wait返回均unread_count=0，末尾ready时为17。`sample_lost_total` 0→1只定位到16-wait采样间隔；reject为0。SHM不是该run中复现空窗的必要条件，但未证明UDP导致问题。
- **决定依据**：EGO实际pose reader QoS为reliable/volatile/KEEP_LAST 25，mapping publisher为reliable/volatile/KEEP_LAST 50；本轮unread_count峰值17，因此不改队列深度。
- **待决问题**：lost计数对应哪个样本、样本何时进入DataReader history，以及reader接收与executor调度各自的作用仍未分清。下一步添加低开销的reader data-available／sample-lost变化标记，并保持现有健康和unknown安全门。
- **证据**：[报告 #349](../../progress/evidence/p2-ego-pose-rmw-transport-ablation-20261021-349.json)、[报告 #350](../../progress/evidence/p2-ego-pose-rmw-udp-primary-pipeline-20261021-350.json)、[改动记录](../../progress/changes/2026-10-21-016-p2-ego-pose-rmw-udp-ablation-349-350.md)。
