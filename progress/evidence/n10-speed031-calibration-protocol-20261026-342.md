# #342 N10.3：0.31 m/s/axis planner 候选受控验证协议

状态：**执行前固定；尚无运行结果。** #340/#341 的 B 样条控制点速度导数最大值为 0.239385 与 0.305505 m/s，原 0.10 m/s/axis 配置的有效门为 0.1051 m/s；#341 的 ratio sentinel 修复没有解决最终曲线拒绝。本次候选 0.31 m/s/axis 仅用于检验 planner 能否生成 16 m 任务曲线，不代表 PX4 实际飞行速度或可接受速度。

## 假设、变量与保护

- 唯一 planner 实验变量：`max_velocity_m_s` 从 #341 的 `0.10` 改为 `0.31`。规划 horizon 2.0 m、逐轴加速度 0.25 m/s²、官方 EGO 策略、地图/相机、16 m 目标、+0.1 m 高度、+0.2 rad yaw 及 PX4 参数保持一致。
- #342 runner 增加运行保护，不改变规划器、PX4 bridge 或任务阈值：从 goal 配置读取既有 `max_actual_vector_speed_m_s=0.12`，监视 EGO READY/COMPLETED 参考速度和 PX4 `VehicleLocalPosition` 三维速度。无效速度样本 fail-closed；任一来源超过 0.12 m/s 即取消当前目标，等候 action 取消响应，再由已实现的 caller `STOP_HOLD` 和唯一 `uav_px4_bridge` 降落流程收尾。参考速度监视是保守代理，不冒充真实速度；真值仍只用于事后评估。
- 该候选可能在低于 0.12 m/s 的飞行速度之前就因参考速度越限而拒绝，这是预定失败条件；不得为通过试验而抬高阈值或关闭监视。

## 通过／停止判据

1. `bash tools/project.sh test` 与 Python 编译通过；固定二进制为已应用 EGO 补丁 0050/0051 的 #341 ROS 构建。
2. fresh 单 D435i Gazebo/PX4 SITL；preflight、官方策略起飞准入、ROS graph、contact、定位与 PX4 新鲜度均按既有规则通过。
3. 若 EGO 拒绝规划、运行速度保护触发或其他现有门失败，记录全量日志；请求安全取消/降落，独立确认 bridge landed、PX4 disarmed 后停止本项目容器。不得将该失败计为长程校准通过。
4. 只有全程参考速度及 PX4 速度均不超过 0.12 m/s、任务成功到点且完成 3 仿真秒 dwell，才执行固定 SE(3) 真值评估和完整 600 仿真秒 ACTIVE hold；地图源龄、tracking、定位、时效、接触与最终 landed/disarmed 的原门限均不变。
5. 最多一个 fresh run；结果对参数的结论只适用于本候选与这次冷启动，不外推为速度/距离保证。

## 固定输入身份

| 输入 | SHA-256 |
|---|---|
| `config/components/mapping/n10_horizon2_calibration.json`（对照） | `e9f780d95c028af7e2809bf4d77a0a994fc86a3fe1cf05bee06324768edcf758` |
| `config/components/mapping/n10_horizon2_speed031_calibration.json`（唯一变量） | `33864323ae310e47d2d268b6ad091037c438a5aeb66bf4b8adcd4b7e3cbf64e0` |
| `config/components/navigation/n10_long_range_vio_calibration_goal.json` | `d1e73365f0cc12d4f30a5445fa25ed54e35267eb2ff80a788c5f3d7162212821` |
| `config/components/navigation/vehicle_envelope.json` | `2c76dc3e91aee1065e1f7095c29f93cb1bb79bdcaefd019ecfa333ff2a902d7c` |
| `config/components/navigation/task_supervisor.json` | `2ebcc06d25a6f550725161d3542915c29989a912ef1d6c8d48e596873980bb56` |
| `tools/run_vio_ego_flight.py`（0.12 m/s guard） | `a5d0794130dcff8a44405db6bde94a0d378fde43a7b407fbe7a766b9cbcbea6d` |
| `tools/speed_guard.py` | `d3e3227407da9c391dad0d564bddd4b621decf56586aa416da0265b396f72da2` |
| `tools/test_speed_guard.py` | `c88980e12a832a6649c38cb561ac6ceb19dc5d489f55b7c5cdb14d47241d19ed` |
| EGO patch `0051-n10-spline-reallocation-ratio-sentinel.patch` | `b41440d75badb304fc59684718a4b2fe9a295d1fc13485c43ee0900161f8b4d1` |

Run ID：`n10-20261026-342-speed031-guarded`。运行原始数据将保存在 `artifacts/runs/<run_id>/`，测量报告为 `progress/evidence/n10-speed031-calibration-20261026-342.{md,json}`。此诊断不计 N11–N16 正式任务次数。
