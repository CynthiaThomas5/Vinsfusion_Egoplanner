# P5 Fast DDS reader-status trace repeat #231

对话摘要：[2026-10-20-021](../../collaboration/dialogues/2026-10-20-021-p5-fastdds-status-trace-repeat.md)。证据：[Fast DDS status、RMW readiness、EGO take 与 PX4 ULog](../evidence/p5-ego-fastdds-status-trace-20261020-231.json)。

## 范围与结果

#231 使用与 #230 相同的固定 Jazzy/RMW Fast DDS 探针、低负载无真值视觉闭环和同一目标。探针仍只挂在 EGO 进程，每128次目标 reader wait 读取一次 DataReader matched、sample_lost、sample_rejected 状态；未改 canonical 源码、QoS、健康门、PX4 参数或控制所有权。

首32.5秒窗口内有557次 camera-pose `rmw_publish` 和536次 successful take，最大 take 间隔2.593229秒。最大 gap 内仍有46次 publish，publisher 最大间隔0.223674秒；700次目标 reader wait 中699次 ready=0、一次 ready=1。最后的 ready 事件距下一次 successful take 23.073微秒；该窗536个 ready=1 与536次 successful take 一一对应，ready→take延迟中位数9.868微秒、P95 25.617微秒、最大3.037毫秒。最大 gap 内没有 readiness trace 序号缺口。

229个状态样本中，首个样本在发现 peer 前为 matched_current=0；其余228个为1。所有 getter 返回码均为0，sample_lost_total 和 sample_rejected_total 始终为0。**最大 take gap 内的5个状态样本**均为 matched=1、lost=0、rejected=0，且前后相邻样本同样保持匹配。该复测重现了 #229 的 reader-not-ready 长空档，同时未观察到 reader unmatch 或状态计数报告的 loss/rejection；这些聚合状态不证明每个 `rmw_publish` 样本已由 RTPS 交付。

导航 action 以 `position_yaw_tolerance_held` 成功，目标位置误差0.06265米；PX4 ULog覆盖34.056仿真秒、dropout为零，EV position/yaw/velocity各30/45个融合状态为 true，GNSS aiding 为零，最终完成 AUTO_LAND、touchdown 和 disarm。结束时 localization 为 `normalized_cost_exceeded`；该运行不构成长时定位健康或正式验收证据。

## 验证与限制

验证包括相同 synthetic status preflight、LTTng/Babeltrace readiness/status/publisher/take 对齐、#231 SITL action/landing、pyulog 汇总及 SHA-256 校验。CTF trace 33个文件；运行产物、原始分析、支持 preflight 和 ULog 的83/83个哈希匹配。原始产物位于 `artifacts/runs/p5-px4-vio-ego-pose-receipt-fastdds-status-trace-20261020-231`。

这两轮 reader-status 对照已确认长空档时读端仍 matched，Fast DDS 的 sample-lost/sample-rejected 累计状态未增长；仍不能区分 RTPS transport delivery、writer history、资源/调度等更底层原因。P5/P6 与 GOAL A–H 仍未完成；F 定量标准尚未冻结，D/E 正式验收未开始。
