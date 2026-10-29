# N07.36 #190：完整 freshness 窗口与 no-goal hover

## 目标与假设

Goal 完成模式，范围 N07。#189 的 freshness probe 在 sim 480.992 结束，之后 hover 前置检查看到 `propagated_stale`。本轮按既定 separated-return 路线保持相同镜像、runtime、spawn、N05 与 health 门限，延长只读 probe 至 `flight.json` 写出并缩短 N05 summary 到 hover 之间的等待，捕获释放至落地的完整定位时间线。运行计划见[对话摘要](../../collaboration/dialogues/2026-10-24-190-n07-full-hover-readiness-timeline.md)。

## 结果

- Run：`artifacts/runs/n07-20261024-190-01/`；image、runtime contract、spawn、wall layout、support profile 固定。
- 初始 N05 online/offline 一致拒绝 raw unknown；支架 12/12。Attached、post-release、current-area online/offline gates 同 epoch/map 接受；N05 summary 14/14。Fixture helper 报 `localization changed or became invalid during physical scan`，但最终 valid、detached/removed、DISARMED/landed；失败字段保留。
- Probe 以 `flight.json` 为 end marker，捕获 10,736 个事件、178.646 秒墙钟和 2.039 秒尾段；窗口内 localization status 保持 TRACKING/valid，未复现 #189 的 `propagated_stale`。
- No-goal hover 30.0 仿真秒 PASS，未发送导航目标，bridge enable/disable 接受，最终 landed/disarmed。PX4 ULog 12/12 通过，EV 融合和 GNSS/truth aiding 配置符合要求，独立定位/保持误差可测。
- Hover evaluator 为 10/11、FAIL；唯一失败是 ROS graph 的 pre-enable snapshot 四个控制话题均为 0 publisher。空中与结束快照都为每话题唯一 `uav_px4_bridge` publisher，无 truth 节点／话题。全快照资格器仍失败，所以 N07 连续数保持 0/3。
- 安全停止：`bash tools/project.sh stop n07-20261024-190-01`；容器 exit 0，无活动项目容器。

详细指标、哈希与停止检查见[证据报告](../evidence/n07-hover-graph-capture-failure-20261024-190.md)及其 JSON。验证命令包括 `python3 tools/debug_truth/evaluate_n07_hover.py artifacts/runs/n07-20261024-190-01`（10/11，按 graph 项失败）、`PYTHONPATH=/tmp/n07-pyulog-packages python3 tools/debug_truth/analyze_n07_ulog.py ...`（12/12）、`python3 tools/diagnostics/reconcile_n07_ros_graph.py ...`（严格全快照检查失败）以及项目结构／diff 检查。

## 局限与下一步

本轮同时将 freshness probe 覆盖到 hover 结果并缩短了 N05 后等待，不能将 #189 的 stale 单因归结为其中一个时间因素。下一项 #191 保持飞行代码与门限不变，仅让 run-local 只读等待器在 bridge ACTIVE 且 armed 后启动原 graph capture，消除 pre-enable 空 publisher 快照导致的资格失败。
