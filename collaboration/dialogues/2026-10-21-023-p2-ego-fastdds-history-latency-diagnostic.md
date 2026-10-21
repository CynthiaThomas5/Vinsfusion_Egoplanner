# GOAL C Fast DDS history-latency metadata diagnostic #360–#361

- **任务摘要**：用 Fast DDS 2.14.6 的 `HISTORY_LATENCY_TOPIC` 元数据检查点，尝试观察 mapping adapter 的相机位姿 writer 与 EGO reader；不读取应用消息 payload。
- **用户约束**：只推进 P0–P6 单 D435i 仿真；保留既有 stage 与工作区改动；真值只允许 debug_truth；不启用控制链；阈值、QoS 与 canonical 配置不因诊断放宽。
- **已做决定**：#360 的 ROS 2 CLI 最小流量 smoke 收到 67 条 Fast DDS 统计样本，说明只读统计 observer 可用。#361 中目标映射 publisher 和 EGO reader GID 均已捕获，但上游 localization 在仿真时钟 4.820 s 处因 propagated 源戳 4.879999999 s（提前约60 ms，超过20 ms门）锁定；独立相机位姿观察者收0帧，MapStatus无深度转发，故该轮不回答目标 DDS reader 问题。
- **结论边界**：目标 GUID 对没有统计样本不能解释为丢包或 history 故障，因为上游没有发出相机位姿样本。未调整20 ms门、QoS、unknown策略或canonical源码；无真值、控制器、PX4、控制topic或goal派发。
- **下一步**：在 run-local trace 中查明仿真 `/clock` 与 propagated pose 源戳的偏差；仅在 localization/MapStatus 持续有效且确认相机位姿 publisher 有输出后，再采目标 GUID 对的 Fast DDS 统计。
- **证据**：[诊断报告 #360–#361](../../progress/evidence/p2-ego-fastdds-history-latency-diagnostic-20261021-360-361.json)、[#360运行清单](../../artifacts/runs/p2-ego-fastdds-history-latency-smoke-20261021-360/run-manifest.json)、[#361运行清单](../../artifacts/runs/p2-ego-fastdds-history-latency-trace-20261021-361/run-manifest.json)。
