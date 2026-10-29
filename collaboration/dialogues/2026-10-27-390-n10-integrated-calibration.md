# N10.3 #390 综合校准

用户指定继续完成 N10.1–N10.7。N15 的十二次正式故障测试和 N16 的正式十分钟验收均在 N10 冻结之后。

#390 成功完成 16 m action、60 仿真秒诊断保持与落地上锁，随后安全停止。该次运行没有可用 truth 样本，资源观察报告也缺失；raw occupancy sphere 请求因半径 0 被拒绝，但旧工具只核对身份，误报为成功。故独立到达、VIO/跟踪、4 ms 物理步净空和资源/队列指标均未通过，保持 `INSUFFICIENT`。

已修复真值 protobuf 字段、资源观察 QoS/中断清理，并修正 raw sphere radius 与 official planning point radius 的区分及 evaluator 接受语义。455 项项目测试与导航/official EGO 集成探针通过。#390 run-local 冻结产物保持原样，#391 将使用修复后的独立副本复测观测链路。

用户约束继续有效：离线验收统计不增加起飞拒绝、取消或降落分支；不恢复项目自加定位/速度健康门或 raw-known-free 全包络门；native PX4、EV 和 EGO 输入 watchdog 保留。N10 当前仍 `in_progress`。
