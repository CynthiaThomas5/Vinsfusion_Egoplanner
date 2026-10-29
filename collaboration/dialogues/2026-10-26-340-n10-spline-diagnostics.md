# N10 #340 最终样条动力学诊断

- **任务**：继续用户明确授权的 N10 Goal 完成模式，当前仍是 N10.3。
- **已知证据**：#337 在 5 m EGO horizon、#339 在 2 m horizon 下都因最终样条速度／加速度可行性失败；#339 的任务前检查通过，规划在约 0.056 sim-s 内拒绝，PX4/bridge 安全落地并 disarm。
- **缺口**：原日志没有逐轴速度／加速度最大值或独立 ratio，不能依据现有结果决定速度值。
- **决定**：只增加 diagnostics-only EGO 补丁 0050。任务、planner 参数、阈值、碰撞策略、相机和控制者全部固定。构建后做一次新的同任务 PX4/SITL；不因失败重复试跑，不放宽阈值。
- **目标产物**：实际最终 spline feasibility 原始日志与 per-axis/ratio 结论；该量测用于选择下一项参数校准，不作为飞行通过。
- **约束**：真值只读；单 D435i Gazebo/PX4 SITL；唯一控制出口 `uav_px4_bridge`；安全落地后停止本项目仿真，不触碰其他容器。
- **结果**：17 个 ROS 包构建通过。#340 有 40 条逐轴诊断行与 10 次最终 spline 拒绝；最大 X 速度控制点导数 0.239385 m/s，高于 0.1051 m/s 有容差门；最大加速度 0.0449998 m/s²，低于 0.2626 m/s² 门。物理失败项是 X 速度。
- **额外发现**：既有时间重分配 `ratio` 把未触发的加速度分量哨兵 `-1` 计算为 2，导致首次 refine 总 ratio 高于速度单项 ratio。#341 将修正该 ratio 的 sentinel handling；任何门限不放宽。此改动需新构建和新 SITL，#340 不作为飞行通过。
- **末态**：contact 评估通过、违规接触 0、landing contact observed；PX4 arming_state=1，bridge LANDED/disarmed，项目容器退出 0。
- **证据**：`progress/evidence/n10-spline-dynamics-diagnostic-20261026-340.md`；运行目录 `artifacts/runs/n10-20261026-340-spline-dynamics-diagnostics/`。
