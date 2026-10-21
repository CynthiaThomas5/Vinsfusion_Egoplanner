# GOAL C EGO UDP receive-meter trace #356–#359

- **任务摘要**：继续定位 #353–#355 观察到的 EGO camera_pose 长 take gap，增加只按 participant UDP socket 与10 ms时间桶统计的 receive API 计数；不采集payload。
- **用户约束**：仅做P0–P6单D435i仿真导航诊断；不混入或回滚既有用户改动，不修改canonical源码、配置、QoS、sysctl，不订阅真值或完整世界地图，不发布控制。
- **决定与修正**：#356因 launch action 的 `additional_env` 覆盖外层 `LD_PRELOAD` 未加载计数器；#357通过节点级环境注入并验证 `/proc` 后仍未落盘；#358增加SIGTERM-safe汇总写出；#359在trace停止后对已记录EGO PID直接发SIGTERM，成功保留汇总。#356–#358仅留作方法迭代，不参与有效计数。
- **结果**：#359重现2.344821 s camera_pose take gap。期间adapter与独立reader各47条位姿、最大源戳间隔66 ms；MapStatus稳定ready且epoch/map_id未变。EGO 638次wait中637次unread=0、末次unread=7；40次状态采样matched=1/lost=0/rejected=0。EGO UDP 62427 socket在gap内有至少2,540次成功receive API调用（完整10 ms桶），计入边界桶上限2,623次；错误0。socket drop增加140。
- **结论边界**：socket汇总包含所有DDS流量且不解码payload；不能认定这些receive调用是camera_pose RTPS样本，也未证明样本进入EGO DataReader history。目标voxel在同身份快照中unknown→free，planner-only probe收到2条未执行B-spline；不构成避障或飞行验收。CTF哈希通过，wait trace缺110–116但在所选gap外。
- **下一步**：先检查不读取payload的topic-scoped Fast DDS/reader元数据观测点，再决定是否需要更细诊断；随后按GOAL C继续vehicle-safe视角、多布局与轨迹执行验证。P2保持passed、GOAL C保持pending。
- **证据**：[报告 #359](../../progress/evidence/p2-ego-pose-rmw-recv-meter-trace-20261021-359.json)、[运行清单](../../artifacts/runs/p2-ego-pose-rmw-recv-meter-trace-20261021-359/run-manifest.json)、[改动记录](../../progress/changes/2026-10-21-022-p2-ego-pose-rmw-recv-meter-trace.md)。
