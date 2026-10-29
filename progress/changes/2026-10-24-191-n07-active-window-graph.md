# N07.37 #191：将 ROS graph 捕获起点移到 ACTIVE 窗口

## 模式、基础与缺口

Goal 完成模式，用户指定范围 N07，当前连续合格冷启动 0/3。#190 的 30 秒 no-goal hover、12 项 ULog 与独立误差测量通过；严格 hover evaluator 唯一失败项是 ROS graph：pre-enable 快照在 1 秒时读到四个 PX4 control topic 均为 0 publisher，而 airborne 与 final snapshots 均读到唯一 `uav_px4_bridge` publisher。全快照 checker 要求每张快照都有唯一 publisher，因此不能将 #190 计入三连。

## 唯一诊断变量

保持固定 image、runtime contract、spawn、wall layout、separated-return profile、N05/health 阈值、hover 程序和评估器完全一致。只将未修改的只读 `capture_n07_ros_graph.py` 的启动时刻改为收到 `/uav_px4_bridge/status` 中 `phase=ACTIVE && armed=true` 后；使用 run-local 只读等待器启动它。该等待器仅订阅状态并调用现有 graph recorder，不发布 topic/service/控制。这样 graph 的首次快照落在控制 publisher 已存在的实际空中窗口，仍保留 recorder 自动记录的结束 landed 快照。

## 子项范围与判据

运行 ID：`n07-20261024-191-01`。复用 #190 完整步骤：初始拒绝；支架 12/12；attached、post-release、current-area online/offline 与 N05 14/14；probe 从 ready marker 采到 `flight.json` 后 2 秒；真值、alignment、bridge 只读记录在 hover 前启动；同一 30 仿真秒 no-goal hover；独立 hover evaluator、ULog 12/12 和 graph reconcile。任何 N05、定位、map identity 或 hover precondition 不通过均不调用 enable、不飞。

本子项只在原 evaluator 全部 11/11、ULog 全部 12/12、graph 空中与 landed snapshots 单 publisher/no-truth、PX4 最终 landed/disarmed、当前 runtime contract 哈希一致时计为一轮合格 cold start。失败保持 0/3；通过则 1/3，并以相同固定组合继续 #192/#193。

## 产物

- Run-local active-window graph wait helper、等待事件、原始 graph capture/reconciliation。
- N05 summaries、full-window VIO probe、flight、truth/alignment/bridge、ULog、hover evaluation。
- 轻量证据、变更与对话记录；不修改源码、配置或验收阈值。

## 实际结果

#191 实际运行目录为 `artifacts/runs/n07-20261024-191-01/`。支架阶段 12/12、N05 三组 online/offline 与 14/14 summary 通过。Fixture helper 保留 `fresh DISARMED status is required for every fixture command` 错误，但记录 detached/removed、final landed、DISARMED，post-release gate accepted。

Graph waiter 确实等到 `ACTIVE && armed`，但 bridge 在 hover 2.64 仿真秒时因 `px4_telemetry_stale` 安全降落，capture 未获得 airborne snapshot。中止样本的 PX4 local-position/attitude 源时间戳相对映射仿真时钟超前约 144/136 ms，高于 65 ms future-age 限值；bridge disable 后最终 landed/disarmed。no-goal hover evaluator FAIL，ULog 12/12 pass，N07 仍 0/3。

验证：`PYTHONPATH=/tmp/n07-pyulog-packages python3 tools/debug_truth/analyze_n07_ulog.py ...`（12/12 pass）；`python3 tools/debug_truth/evaluate_n07_hover.py artifacts/runs/n07-20261024-191-01`（短于30秒并缺 airborne graph，FAIL）；`python3 tools/diagnostics/reconcile_n07_ros_graph.py ...`（FAIL，缺 airborne snapshot）；`bash tools/project.sh stop n07-20261024-191-01`（容器 exit 0）。详细 source-age 样本和哈希见[证据报告](../evidence/n07-px4-telemetry-stale-20261024-191.md)。

## 限制与下一步

本轮直接证实 bridge 因 PX4 local-state source time 超前门限 fail-closed；尚未判定时间偏差来自 clock mapper、PX4 timestamp 还是负载调度。下一项 #192 保持运行/控制条件不变，只取消额外只读 freshness probe，观察必需记录负载下是否再次越过同一门限。
