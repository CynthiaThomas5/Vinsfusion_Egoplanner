# P2 EGO 窗口内 timeout 复现与调度诊断

日期：2026-10-17。对话摘要：[2026-10-17-007-p2-ego-timeout-scheduling-diagnostic.md](../../collaboration/dialogues/2026-10-17-007-p2-ego-timeout-scheduling-diagnostic.md)。

- 修改：为 run #24 建立负向运行证据并更新当前进度、契约、项目说明与 EGO 补丁说明。该记录没有将 run #24 计为稳定建图通过。
- 运行：使用 Ground-height EGO overlay、`ground_height=-0.15 m`、`odom_depth_timeout=0.4 s` 和连续 executor observer；深度 READY、定位 TRACKING，窗口40.026 s，共415组配对 depth/pose。源间隔 p50/p95/max 0.033/0.132/0.429 s，接收源龄 p50/p95/max 0.074/0.110/0.638 s；前三组告警附近源间隔最大0.231 s。地图点数变化140次，最大1973点。
- 结果：EGO 在 probe 测量窗内记录73条 timeout（13.729–14.125、15.115–15.973、22.375–23.266 仿真秒），另6条在观测结束后的运行尾段。每组告警的最近同步 camera pose 都在地图内；独立 observer 在相同时间范围收到配对输入。因此 run #24 是失败/no-fault场景证据，不计清洁观测。调度/同步 backlog 是待验证假设。
- 源码观察：`ego_planner_node.cpp` 使用 `rclcpp::spin(node)`；`GridMap` 的 synchronized input 与50 ms occupancy timer 使用默认 callback group；timer 执行图像投影与 raycast。此结构可导致单线程回调延迟，但还没有实测耗时数据。
- 验证：run #24 原始报告、日志及产物已保留于 `artifacts/runs/p2-ego-map-healthy-input-20261017-24` 并在 P2 输入间隔报告记录 SHA256；运行后进程审计和代码/文档检查待本轮完成。
- 限制与下一步：run #23 是唯一一次40秒无 timeout 的 timing-quality 样本。0.4 s timeout 和 -0.15 m map lower bound 仍为 PROVISIONAL。先加 steady-clock 输入年龄、occupancy timer 间隔／回调耗时诊断并重跑，再评估 active stale，不做未经线程安全审查的多线程器修复。
