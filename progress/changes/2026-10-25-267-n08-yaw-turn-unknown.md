#267 运行与证据记录

## 目标

在 #266 连续 B-spline 管道检查修正后，用 fresh N05 入口完成 N08 低速前向制动，并按用户要求验证“先原地转头约 180°，再由 EGO 机头前向返航”。

## 结果

- N05 支架扫描完成 15/15，post-release 和 mission current-area admission 均通过；同一 epoch/map_id，40.003 s preflight 通过。
- 0.6 m EGO 前向目标执行成功，在线连续 reference tube 证书通过。独立真值测得参考峰值 0.08082 m/s、实际水平峰值 0.08100 m/s、停止距离 0.28794 m、减速响应估计 0.844 s、最大跟踪误差 0.07862 m。
- yaw 前置 raw hold 查询以 30 个 unknown 拒绝，未执行 yaw 或返航。pre-turn map 与起飞前 ground map 同身份；逐格对比为 30 个 `free→unknown`，全部位于当前机头后方的同一 x 层，未发现 occupied。
- 飞行器实际安全落地并 disarm；桥 `LANDED/control_enabled=false`，PX4 `arming_state=1/landed=true`，项目容器已停止。

## 检查命令

- `python3 tools/debug_truth/evaluate_n08_braking.py <isolated-copy-of-run>`：无绘图离线评估完成并生成 JSON；制动测量检查通过，任务总评因 yaw/return 未执行而为 `passed=false`。
- `PYTHONPATH=tools python3` 只读复算 ground/pre-turn raw sphere、体素状态变化及 +0.22 m 候选 capsule：候选 hop 9/9 查询 raw-free，候选转向球 raw-free；尚未转向的 return capsule 仍有 unknown。
- `ros2 topic echo --once` 读回 `/uav_px4_bridge/status`、`/fmu/out/vehicle_status_v1` 与 `/fmu/out/vehicle_land_detected`：LANDED、disabled、disarmed、landed。
- `bash tools/project.sh stop n08-20261025-267-yaw-first-return`：退出码 0。

## 产物与局限

- 详细结果：[evidence JSON](../evidence/n08-yaw-first-return-unknown-20261025-267.json)、[报告](../evidence/n08-yaw-first-return-unknown-20261025-267.md)、[对话摘要](../../collaboration/dialogues/2026-10-25-267-n08-yaw-turn-unknown.md)。
- 原始运行位于 `artifacts/runs/n08-20261025-267-yaw-first-return/`。
- rearward unknown 的精确 mapper 成因仍未唯一确定。+0.22 m 是归档图上的候选筛选结果；#268 必须用新 epoch、新鲜 N05 与在线地图逐阶段重新准入。速度限制、unknown 处理、tracking margin 和原 0.6 m 制动目标均未调整。
