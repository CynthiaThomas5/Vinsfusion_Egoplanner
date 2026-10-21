# P5 Fast DDS reader-status trace repeat #230

对话摘要：[2026-10-20-020](../../collaboration/dialogues/2026-10-20-020-p5-fastdds-status-trace-repeat.md)。证据：[Fast DDS status、RMW readiness、EGO take 与 PX4 ULog](../evidence/p5-ego-fastdds-status-trace-20261020-230.json)。

## 范围与结果

#230 延续 #229 的固定镜像、无真值单 D435i VINS/EGO/PX4 组合，给 EGO 进程加载 run-local Fast DDS reader-status 探针。探针每128次目标 reader wait 采样 matched、sample_lost、sample_rejected；固定 RMW/Fast DDS 为 rmw_fastrtps_cpp 8.4.4 / Fast DDS 2.14.6。synthetic preflight 的基线和插桩各收取800/800条 reliable 消息、零缺口；status getter 均成功。探针及启动 overlay 的来源、哈希和作用域见 run-local `probe-launch-provenance.json`。

在首32.5秒窗口内，camera-pose 有555次 `rmw_publish` 和555次 EGO successful take，最大 take 间隔0.259119秒；同一段 publisher 最大间隔0.259002秒。555个 reader-ready 与555次 successful take一一对应，ready→take延迟中位数6.672微秒、P95 18.605微秒、最大2.564毫秒。最大 gap 内的68次 wait 有67次 ready=0、一次 ready=1；该 ready 事件距下一次 successful take 6.792微秒。

共采样223次 reader 状态，getter 返回码均为0；每次 matched_current=1、sample_lost_total=0、sample_rejected_total=0。最大 take gap 内的单次状态样本也报告 matched=1 且 lost/rejected 均为0。该轮没有重现秒级空档，因此不能用它判定 #229 的 RTPS 投递或 writer history 根因。

导航 action 以 `position_yaw_tolerance_held` 成功，目标位置误差0.05483米；PX4 ULog覆盖31.74仿真秒、dropout为零，EV position/yaw/velocity各28/40个融合状态为 true，GNSS aiding 为零，最终完成 AUTO_LAND、touchdown 和 disarm。结束时 localization 为 `normalized_cost_exceeded`，所以本轮属于成功任务的诊断复测，不是长时健康或正式验收。

## 验证与限制

验证包括 synthetic status preflight、LTTng/Babeltrace readiness/status/publisher/take 对齐、#230 SITL action/landing、pyulog 汇总及 SHA-256 校验。CTF trace 33个文件；运行产物、原始分析、支持 preflight 和 ULog 的83/83个哈希匹配。原始产物位于 `artifacts/runs/p5-px4-vio-ego-pose-receipt-fastdds-status-trace-20261020-230`。

本探针只读取 DataReader 聚合状态；matched 和累计 loss/reject 计数正常，不代表每个发布样本均已通过 RTPS 到达。P5/P6 与 GOAL A–H 仍未完成；F 定量标准尚未冻结，D/E 正式验收未开始。
