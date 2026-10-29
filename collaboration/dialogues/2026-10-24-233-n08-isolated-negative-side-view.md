# N08.2w #233 任务摘要

- #232 在 9/19 stage 因 `normalized_cost_exceeded` 中止；其 profile 在负 Y 水平观察前先执行 yaw +π/2、pitch −0.45，所以没有检验 #231 的负 Y unknown。
- #233 仅替换侧向观测姿态段为 yaw −π/2、pitch 0 后回中，保留相同 overhead/ground scan 前 9 阶段和其余配置。
- 添加明确 profile 并更新 N05 runner/probe allowlist；先运行 DISARMED scan，只有 fresh same-identity N05 admission 通过后才进入 compute-only。
- 检查起点 hold、轨迹与 0.50 m stop corridor；不执行 XY，不把 map clearance 视作动态停车证明。

## 实际结果与交接

- 新 profile 静态 profile 单测 28 项通过；N05 scan 完成 16/16，负侧水平 yaw 到达，post-release/current-area online/offline gates 同身份通过。
- fixture helper 的最终 `fresh DISARMED status` error 保留；fixture model absent、独立 landed readback 和后续 mission final landed/disarmed 均确认。写入 `n05-monitor-resolution.json` 后清除旧监护标记，仿真容器已停止 exit 0。
- 同 run compute-only 以 `planner_full_curve_unknown` 中止，无 B-spline / READY / XY。失败态 same-map query：start body 36 unknown、start hold 394 unknown、goal hold 472 unknown。
- 下一项 #234：保持 overhead scan 与门限不变，沿已通过的 −π/2 转至 −π 后回中，观察后向 unknown；仍仅 DISARMED scan + compute-only。
- 证据：[报告](../../progress/evidence/n08-isolated-negative-side-view-20261024-233.md) 和同名 JSON。
