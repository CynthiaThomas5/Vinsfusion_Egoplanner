# P2 EGO clock/domain 对照诊断

日期：2026-10-17。对话摘要：[2026-10-17-015-p2-ego-clock-domain-diagnostic.md](../../collaboration/dialogues/2026-10-17-015-p2-ego-clock-domain-diagnostic.md)。

- 范围：在 patch 0016 诊断 overlay 上复测 EGO pose reader 延迟。#45/#46 使用运行目录内的 `/clock` wall-rate relay；#47–#49 使用原始 `/clock` 对照 domain/partition；#50 在 domain186 仅对当前 run 设置 Fast DDS `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`，依据已安装 Fast DDS 2.14.6 的官方环境变量文档。所有差异只在 artifacts 运行目录，不改自维护、vendor、project config 或 PX4 控制代码。

| Run | ROS domain | Clock | 配对样本 | pose P95 / 最大 | >0.1 s | EGO clock take |
|---|---:|---|---:|---:|---:|---:|
| #45 | 186 | 限频 relay | 434 | 0.369 ms / 0.530 s | 3 | 4,586 |
| #46 | 186 | 限频 relay | 423 | 0.524 ms / 2.062 s | 14 | 4,445 |
| #47 | 187 | 原始 | 540 | 0.365 ms / 3.640 ms | 0 | 46,803 |
| #48 | 186 | 原始 | 498 | 322.7 ms / 1.541 s | 30 | 44,874 |
| #49 | 186 | 原始 | 536 | 228.9 ms / 1.958 s | 32 | 46,999 |
| #50 | 186 | UDPv4-only | 241 | 1.925 s / 2.820 s | 49 | 48,413 |

- 结果解释：限频后仍有批量 pose take 延迟，因此 clock callback 负载没有被证明为根因。domain187 的一次未限频运行无长尾；domain186 的两次未限频运行重现长尾。#49 换新 Gazebo partition 后仍复现，说明不能只归因于 #45/#46 使用的 partition；domain ID 相关性仍可能与启动时序、运行负载或 middleware 状态混淆。#50 UDPv4-only 后配对数降到241、mapper pose 最大发布间隔升至1.044 s，说明这次 transport 变更同时改变了源节奏，不能用来判定共享内存是否导致域186长尾，也不建议作为项目配置。所有六个 run 的 mapper pose/depth 发布 source timestamp 与 EGO `rmw_take` 完全对应，trace 丢失数为0。#49 runtime graph 显示 `/clock` 单 publisher、camera pose 单 publisher/单 EGO subscriber 和预期 application node。
- 环境线索：容器内存在不同 domain 的 Fast DDS 共享内存对象及 ROS CLI daemon，包括 domain186/187；运行后未清理任何 daemon 或 `/dev/shm` 对象。没有证据表明这些对象导致延迟。
- 排除尝试 #51：尝试用运行目录 `ROS_HOME` 隔离 domain186 ROS CLI daemon，但 CLI 返回 daemon already running，未获得隔离。probe 因定位适配器锁定 `imu_stale` 而 exit 1，零配对样本；raw VINS-only probe 有输出，但不构成定位/建图健康证据。#51 trace 不纳入统计，原始文件见单独 manifest。此尝试可能停止了原有 domain186 CLI daemon，随后已用默认 ROS_HOME 和 domain186 重新启动；当前 daemon 状态已恢复。
- 验证：六个有效 probe 均 exit 0；六个有效 UST trace 均报告0个丢事件；mapper pose/depth 全量 source timestamp 均一一对应 EGO take。六个有效 run manifest 与 #51 排除 manifest 的每个文件均通过大小与 SHA-256 复核；七个 harness `bash -n`、七个 analyzer 与 clock relay 的 Python AST 检查通过；证据和里程碑 JSON 可解析。`python3 tools/project_status.py` 报 PASS（仅结构／设计检查）；`git diff --check` 与 `git diff --cached --check` 通过。无源码改动，因此未运行 colcon 构建。
- 进程审计：没有运行中的 Gazebo、VINS、EGO、mapping、localization 或 probe 进程；容器保留既有 defunct VINS 子进程及 ROS CLI daemon（domain 186/187），domain186 daemon 已恢复；LTTng 无活动 tracing session。未 stage、commit 或 push。
- 局限：每个组合只观测一个60秒窗口；domain187 与 domain186 的应用图、配置和算法相同，但 middleware 环境和顺序运行会影响结果。未采内核调度、DDS reader-ready 状态或 executor ready-entity 证据。timeout 日志数量是症状记录，不作为阶段验收指标。
- 下一步：使用新的隔离 middleware state 复跑 domain/partition 对照并诊断 Fast DDS reader notification 与 EGO executor 选取。保持 patch 0016 为诊断用途；0.4 s timeout、`ground_height=-0.15 m` 仍为 PROVISIONAL，不启用未加锁的多线程 EGO。P2 与 GOAL.md 目标继续进行。
