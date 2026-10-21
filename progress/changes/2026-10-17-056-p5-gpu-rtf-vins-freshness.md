# P5 NVIDIA EGL/GPU 加速与 VINS freshness 诊断

对话摘要：[2026-10-17-056](../../collaboration/dialogues/2026-10-17-056-p5-gpu-rtf-vins-freshness.md)。

- GPU pass-through与surfaceless EGL已确认使用RTX3060/NVIDIA。GPU map/EGO RTF约0.66，CPU-only #121约0.37；GPU VINS/localization RTF约0.81，CPU-only #114约0.42。GPU有使用采样，observed_offset漂移仍接近`RTF−1`。
- #123短暂产生40组同stamp地图输入、最多1,188点后定位报`propagated_from_future`；#124完整导航profile在目标前锁定，无goal/map/VIO。#125在原始VINS准备前启动adapter，因telemetry_stale未输出VIO。
- #126 run-private warmup helper有属性赋值错误并在profile前退出；#127修正后按现有health.json限值等待10个健康配对，warmup约4.06秒通过。随后定位TRACKING，约1.55秒后因0.337秒VINS imu_propagate收包间隙锁定`propagated_stale`；PX4收28条VIO但无EV融合。所有运行disarmed、bridge DISABLED、控制/truth为零。
- 结论：GPU改善仿真吞吐，但未通过VINS freshness或P5融合；不调整阈值、相机或PX4滤波。详见[轻量证据报告](../evidence/p5-px4-gpu-rtf-vins-freshness-20261017-122-127.json)。

run-private shell语法与Python编译检查通过；时钟与资源指标离线复算，artifact和源码SHA已保存。下一步用统一monotonic时间线追踪VINS publish→localization take、源时间戳、收包年龄和CPU/GPU采样，不放宽门限。之后重跑稳定VIO/PX4与活动建图规划资格。P5仍进行中，P4/P6与GOAL A–H未完成。
