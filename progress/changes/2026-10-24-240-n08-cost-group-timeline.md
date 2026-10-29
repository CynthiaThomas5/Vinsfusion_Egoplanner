# N08.2ad #240：cost 分组 observer

## 改动

- N08 timeline helper 以配置的 normalized cost limit 计算 telemetry 总 cost，保留 visual、IMU、marginalization 的组成本／残差数、cost 评估状态和压缩 prior 指标。
- threshold 状态变化会使该 telemetry 立即落盘；采样间隔仍为 100 ms。
- N05 run input manifest 在 source timeline 模式下记录 localization health config 哈希。
- 新增 telemetry summary 和 threshold transition 单测。没有更改 PX4、健康门限、控制或任务路线。

## 验证和运行

- 58 项定向单测通过；runner shell syntax、三个相关 Python AST、健康配置 JSON、git diff check 通过。
- run n08-20261024-240-cost-group-timeline-01：N05 before 因 ground_plane_insufficient_raw_occupied_voxels 拒绝；DISARMED support scan 在 16/22 因 normalized_cost_exceeded 中止。
- Health.metrics 首个 crossing stamp 与 raw VINS telemetry 精确对齐，cost=1.002603487；随后 1.056 sim s 内记录 9 条过限 telemetry。首帧 marginalization 占 69.8%、IMU 12.4%、visual 17.8%，分组和与 prior 结构检查通过。
- HRT/ROS /clock 差 −8…+16 ms，桥接时间域全有效；健康锁定后 PX4/adapter pair gap 增大。无 post-release N05、compute-only、goal 或 XY。
- helper报告的最终状态需 fresh readback 复核。只读状态确认 DISARMED、landed、at-rest，fixture detached/model absent；project.sh stop 后退出 0。

详情：[报告](../evidence/n08-cost-group-timeline-20261024-240.md)、[JSON](../evidence/n08-cost-group-timeline-20261024-240.json)；对话：[摘要](../../collaboration/dialogues/2026-10-24-240-n08-cost-group-timeline.md)。
