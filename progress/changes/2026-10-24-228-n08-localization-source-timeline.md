# N08.2r #228：定位源时间线与同图停止区域复核

## 假设与判据

- #227.2 的 `LocalizationStatus` 在约 sim 513.38 s 后锁存 `telemetry_stale`，但原 run 没记录 raw VINS ROS 到达时间，无法区分发布、DDS 接收和 adapter 配对边界。
- 唯一代码干预为只读 source/receipt observer；不改定位器、健康门、时钟阈值、N05/N06 参数或控制路径。
- 判据：通过 fresh N05 gate 后，在 compute-only 运行窗口同时记录 raw VINS、adapter odometry、LocalizationStatus、MapStatus 与 `/clock`；继续要求所有控制保持隔离、cancel/bridge hold/落地有效；不执行 XY。

## 实际结果

- Run `n08-20261024-228-localization-timeline-01` 完成。约 39.5 s、29,136 事件、单一 epoch；未复现 `telemetry_stale`。794/794 LocalizationStatus 均 valid，reason 为 `fresh_inputs_and_usable_solver`；174/174 MapStatus 均 ready。raw VINS telemetry/optimized odometry 各 536 条且最大 source gap 68 ms；adapter optimized 最大 source gap 68 ms；`/clock` 无回退。
- N05 支架扫描完成 15/15；扫描前门拒绝 `ground_plane_insufficient_raw_occupied_voxels`，扫描后 post-release 与 mission current-area online/offline gate 均接受且 identity 一致。fixture helper 原样报告 `fresh DISARMED status is required for every fixture command`；独立模型列表确认 fixture 不存在，车辆 landed，不能把 helper failure 改写为 pass。
- compute-only runner 通过：一条 READY 曲线、cancel accepted/confirmed、桥接保持 2.0 仿真秒、landed/disarmed；12 项专用 evaluator 全通过。无水平控制执行。
- 同图曲线证书通过速度上界（0.099957 m/s < 0.15 m/s），但 geometry 失败：起点 hold sphere 半径 0.980618 m 内有 71 个 unknown。其它 start/end body、end terminal hold 和 43/43 sweep 查询通过。N08 execute 仍未授权，minimum deceleration、response-delay bound、actual stop distance 均无测量。
- PX4 readback 的 `MPC_ACC_HOR=3`、`MPC_ACC_HOR_MAX=5`、`MPC_JERK_AUTO=4`、`MPC_XY_VEL_MAX=12` 仅为最大约束，不能证明最小制动能力。
- raw map 在 spline 后约 271 s 获取，但同 epoch/map；fusion/source age 为 28/104 ms。第一次请求被 `no_fresh_fused_depth` 拒绝；之后用独立记录的同一 goal/epoch/map 恢复捕获。该快照不是 spline 同时刻地图，原始 MapStatus 拒绝响应没有重建。

结论：本次 compute-only 时间线健康，#227 stale 未复现但根因仍未知；地图仍未证明起点 hold 球 free；实际停止包络不成立，无 XY／制动证据。完整指标和 SHA-256 见 [#228 evidence](../evidence/n08-localization-source-timeline-20261024-228.md) 与 JSON。

## 后续

N08.2s #229 在 #228 场景和全部门限不变的条件下，只增加 yaw=−π/2 的单侧水平观察及回中，不加第二侧 +π/2 观察。检测起点 hold unknown 是否减少；保持 DISARMED 支架扫描，无 XY。若 N05、定位健康或同图查询不通过，保留拒绝并继续锁定。
