# N03 深度实际融合连续性证据

状态：**通过（静态未解锁 SITL 范围）**。完整机器可读摘要：[JSON](n03-depth-fusion-continuity-20261022-090.json)。

## 诊断门

沿用已配置的 plan_env 0.4 仿真秒融合／源龄门和 adapter 队列上限 8。合格 idle epoch 要求：深度与位姿源戳在 adapter 与 EGO 入口保持配对；同步接收与融合完成持续推进；融合完成仿真时间间隔、回调及融合时源龄不超过 0.4 秒；启动后 MapStatus 持续 `input_ready`；无 trace 计数缺口；队列高水位不超过 8；使用当前身份的只读地图查询至少有重复 fresh 成功样本。plan_env 的曲线准入对已完成融合快照调用 [`queryReadiness(..., false)`](../../src/vendor/ego_planner/planner/plan_env/src/grid_map.cpp)，仍检查 epoch/map_id、相机位姿在图内、超时及同一 0.4 秒源龄；球查询服务在[此处](../../src/vendor/ego_planner/planner/plan_env/src/grid_map.cpp)另外拒绝待处理回调。前者允许读取最新完成融合的地图，即使下一对输入正在等待处理。

## 三次合格 idle fresh epoch

| 运行 | wall 秒 | epoch | EGO 同步对 | plan_env 融合 | 最大融合间隔（sim 秒） | 最大源龄（sim 秒） | adapter 队列高水位 | fresh 查询 | 门 |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| `n03-fusion-20261022-090-01` | 150.05 | `d00e7534177b49d696c9b44b0a63e357` | 3394 | 1740 | 0.104 | 0.156 | 4 | 372/590 | pass |
| `n03-fusion-20261022-090-02` | 150.07 | `df676b0c309a472da3df4b3a4f0a087a` | 3436 | 1751 | 0.108 | 0.156 | 3 | 404/595 | pass |
| `n03-fusion-20261022-090-04` | 150.07 | `873c93bf204e43398ad93e9540865cb9` | 3424 | 1764 | 0.112 | 0.152 | 4 | 358/596 | pass |

三次分别来自独立 PX4/Gazebo/VINS 冷启动，runtime contract SHA256 完全一致：`c282fbf2644770a260b11cc85c8eb7378a2e9cac5f1b68ae8c04701ea076ed7f`。各次 EGO 图像与 pose source stamp mismatch 为 0；trace callback/fusion 计数缺口为 0；PX4 只观察到 DISARMED，导航命令数为 0。三次稳态阶段 adapter dropped-depth 计数增量均为 0，队列峰值低于 8。容器内存峰值分别约 1.72、1.56、1.53 GiB。

查询服务在正常运行中还出现 `no_fresh_fused_depth` 拒绝：第 1／2／4 轮分别为 218／191／238 次；它是在新同步输入已到、占据回调尚未完成时采取的保守拒绝。所有已接受响应的源龄峰值分别是 0.168、0.164、0.164 秒；完整融合 trace 的最大间隔分别是 0.104、0.108、0.112 秒，均低于预设 0.4 秒门。探针单独记录这两种语义；没有改查询、规划或健康门限。

## 断流与 reset

`n03-fusion-20261022-090-fault` 将 Gazebo depth 仅重接到 relay 输入，探针转发 300 帧后丢弃约 2.015 秒，再恢复。DepthHealth 按 `READY → STALE(depth_stale) → READY` 转换，STALE 持续 1.008 wall 秒；adapter 关闭输入门、创建新 map_id，并获得 plan_env reset ack。旧身份查询被拒绝（`map_id_mismatch`）；新身份恢复了 1571 次融合及 300 次 fresh accepted query（最大源龄 0.184 仿真秒）。故障窗口整体 continuity gate 按预期为 false，最大融合间隔包含注入的断流，不能拿它作为正常输入连续性通过样本。

## 保留失败与范围

第三次初始冷启动 `n03-fusion-20261022-090-03` 在 wall 0.437 秒因既有 VINS `telemetry_stale` fail-closed，adapter 清图，未形成 EGO 融合；它保留为失败，不计入三次合格 epoch。随后 telemetry/odometry topic 持续约 11.5 Hz，但本轮没有修改或放宽 N02 健康策略。

该证据只关闭 N03 当前要求的 idle fusion 连续性与断流身份恢复子项。它不替代 N09／正式目标任务里的飞行期连续性，也不改变 B/C/E 最终验收条款。

构建：`bash tools/project.sh build ros`（17 包通过）；回归：`bash tools/project.sh test`（223 项通过）；结构检查：`python3 tools/project_status.py`（仅结构／设计通过）；0040 反向 patch dry-run 通过。所有仿真均经 `bash tools/project.sh stop <run_id>` 安全停止。
