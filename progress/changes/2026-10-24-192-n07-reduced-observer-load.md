# N07.38 #192：保持飞行门限，取消可选 freshness probe

## 模式与基础

Goal 完成模式，用户指定范围 N07，连续合格 cold start 为 0/3。#191 的 attached/post-release/current-area N05 gate 与 14/14 summary 通过；hover enable 后 2.64 仿真秒时，PX4 local-position/attitude 源戳相对映射时钟分别超前约 144/136 ms，超过既有 65 ms future-age 门，bridge 自动降落。#191 严格 evaluator 失败，已落地上锁。

## 单一假设与变量

假设：额外的 VIO freshness probe 同时订阅图像、IMU、VINS telemetry/odometry 与定位状态并累计处理事件，可能增大 cold-start 任务阶段的调度负载，促成桥侧 PX4 source-age 偏差。#192 唯一变化是关闭该可选只读 probe。运行镜像/runtime、N05 支架动作、health/N05/bridge thresholds、no-goal hover 脚本、truth/alignment/bridge 必需记录器、ACTIVE 后 graph capture 等都与 #191 一致。

## 执行步骤与出口

运行 ID：`n07-20261024-192-01`。先完成初始拒绝、12/12 DISARMED 支架扫描、attached/post-release/current-area online/offline 与 N05 14/14；状态、identity、fixture removal 或任一 freshness 条件不满足时不启动 hover。通过后立即启动只读 truth/alignment/bridge 记录器及 #191 的 graph-active-wait helper，运行相同 30 仿真秒 no-goal hover。VIO health 由 flight 的 localization/bridge histories 与独立评估器核查；不启动 `probe_vio_stream_freshness.py`。运行后执行 ULog 12/12、同一 11-check evaluator、ROS graph reconcile，并确认最终 landed/disarmed。

只有原 evaluator 11/11、ULog 12/12、graph active/landed 唯一 bridge owner、30秒 hover 与最终安全状态全部通过才计一轮；失败保持 0/3。不得更改 65ms source-future 限值或用短 hover 代替出口。

## 产物

Run artifacts、只读 active-window graph 等待器、N05 summary、flight、truth/alignment/bridge、ULog、hover evaluation、证据报告、变更与对话摘要。不修改代码、控制参数或配置。

## 实际结果

运行 `n07-20261024-192-01` 完成。初始 N05 online/offline 一致拒绝；支架扫描12/12。attached、post-release、current-area gate 均接受且同epoch/map，N05汇总14/14。fixture helper错误 `fresh DISARMED status is required for every fixture command` 保留；独立状态、场景列表和N05 summary确认支架已安全移除。

No-goal hover完成30.0仿真秒（33.512墙钟秒），无导航goal和position command；定位与PX4 telemetry稳定，正常disable并最终landed/disarmed。没有运行可选freshness probe。独立PX4 ULog 12/12、active-window graph三快照reconcile通过；N07 evaluator 11/11通过。原bridge状态记录中同一phase的详情更新会重复输出，未经处理的raw timeline令评估器报“Need one complete PRESTREAM-to-LANDED flight”；raw文件保持，另存可复算的连续phase折叠视图和hash manifest，使用未修改evaluator完成评估。该转换不改时间戳、状态、阈值或飞行记录。

结果为 N07 合格连续序列 **1/3**。详细指标、唯一publisher、EV/no-GNSS、误差、hash及限制见[证据报告](../evidence/n07-no-goal-hover-20261024-192.md)和JSON。容器按 `bash tools/project.sh stop n07-20261024-192-01` 停止并确认Exited(0)，没有活动项目容器。

## 验证命令与限制

- `PYTHONPATH=/tmp/n07-pyulog-packages python3 tools/debug_truth/analyze_n07_ulog.py artifacts/runs/n07-20261024-192-01/px4_sitl_default/log/2026-10-23/23_06_03.ulg --output artifacts/runs/n07-20261024-192-01/px4-ulog-analysis.json`：12/12 PASS。
- `python3 tools/diagnostics/reconcile_n07_ros_graph.py artifacts/runs/n07-20261024-192-01/ros-graph-audit.json --output artifacts/runs/n07-20261024-192-01/ros-graph-audit-reconciled.json`：3/3 snapshots PASS。
- `python3 tools/debug_truth/evaluate_n07_hover.py <run-local phase-transition evaluation directory>`：11/11 PASS；原始timeline直接输入因重复same-phase行不能解析，raw与派生输入均已存档。
- `python3 tools/project_status.py`：PASS（结构／设计检查，不是SITL证据）；`git diff --check`：PASS。

单次不运行probe的通过与#191遥测过期结果相容，但不能单独确证负载因果。N07仍需连续3次；下一步#193按完全相同固定recipe做新的独立cold start。
