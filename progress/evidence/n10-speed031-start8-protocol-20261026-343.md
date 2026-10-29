# #343 N10.3：spawn -8.0 m 单变量几何诊断协议

状态：**执行前冻结**。该运行属于 N10.3 校准，不计 N11–N16 正式次数。

## 假设与唯一变量

#342 在 −6.5 m 起点、2 m EGO planning horizon 下发送目标后，planner 因 terminal point in obstacle 拒绝，未生成 READY 曲线。源场景在 (−4, 0) 有半径 0.30 m、高 10 m 的圆柱；其顶部约 z=+2.5 m。#342 的第一个前向 local target 推断约在 x=−4.5 m，落入圆柱和 0.7306 m 膨胀半径范围。由于 planner 没记录精确拒绝点，此因果关系仍是几何推断。

唯一主变量：使用 run-specific PX4/Gazebo spawn profile 将世界 x 从 −6.5 m 改为 −8.0 m；z、姿态和 y 不变。该 profile 只由本次环境变量加载，全局 `config/runtime.json` 字节不改。假设首个 +2 m local target 落在 x≈−6 m 后，不再因该圆柱的 inflated occupied 几何而拒绝；随后 planner 仍必须在 live map 和原碰撞谓词下接近并绕行。

## 固定项与保护

- 一次 fresh 单 D435i Gazebo/PX4 SITL 冷启动；同一个 `ego.sdf` 世界和模型。
- mission 相对当前 VIO odom 起点：+16.0 m X、+0.10 m Z、+0.20 rad yaw；goal position/yaw 容差、3 s dwell、360 sim-s action timeout 不变。
- Planner 固定 `max_velocity_m_s=0.31`/axis、`max_acceleration_m_s2=0.25`/axis、2.0 m horizon、0.730617917 m inflation；official_ego inflated-occupied policy 不变。
- 既有 runtime 向量速度 guard 固定 0.12 m/s，同时监视 READY/COMPLETED EGO 参考速度和 PX4 `VehicleLocalPosition`；无效样本、超限、定位或时效门失败均按现有取消、STOP_HOLD/bridge-owned landing 收尾。参考速度越限时即失败，即使 PX4 尚未越限。
- 不关闭或缩小碰撞／膨胀／健康／时效／接触门；真值只用于独立离线评估，绝不输入规划或控制。

## 判据与停止

此 run 仅在以下链条全部完成时支持这个 planner 候选进入后续校准：spawn pose 与 profile hash 匹配；preflight、takeoff admission 和 ROS graph 通过；EGO 生成与当前 goal 同身份的 READY 曲线并持续重规划；guard 无故障且参考和 PX4 实际速度均不超过 0.12 m/s；独立真值到达评估满足 3 s 目标驻留；ACTIVE hold 完成 600 sim-s；地图、定位、时效、接触和最终 landed/disarmed 指标均完整有效。

任一 planner 拒绝、speed guard、健康／时钟／地图、任务超时或接触门失败即完整保留失败数据；禁止同参数反复重启或事后调门限。到点但 600 sim-s hold 或独立评估不完整也不通过。单次通过也只支持该 profile 和该冷启动，不是跨 run 安全保证。

## 运行命令

```bash
D435I_N08_MODE=execute \
D435I_N09_CONTACTS=1 \
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon2_speed031_calibration.json \
D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json \
bash tools/project.sh sim n10-20261026-343-speed031-start8-r01

docker exec d435i-n10-20261026-343-speed031-start8-r01 \
  bash /workspace/tools/n09_runtime.sh \
  n10-20261026-343-speed031-start8-r01 \
  config/components/navigation/n10_long_range_vio_calibration_goal.json \
  n10_calibration
```

运行结束后先由 runner 关闭 Offboard/请求降落，再独立确认 `uav_px4_bridge=LANDED/control disabled` 与 PX4 `disarmed/landed`，最后仅停止该项目容器。未确认安全终态前不停止控制链。

## 运行前验证

首次启动在 PX4 执行前因 resolver 相对路径错误而退出：`sim_runtime.sh` 当时已切入 PX4 build 目录，却用相对路径 `tools/resolve_sim_spawn.py`；无 `spawn-pose.json`、PX4 进程或 flight record，Gazebo 容器以 exit 2 结束。修复为 `/workspace/tools/resolve_sim_spawn.py`，并新增回归覆盖；该次不构成 SITL 飞行或 planner 探索。另一次在容器创建前因预置 run 目录被 wrapper 正确拒绝，同样没有进程启动。以上前置事件见 [#343 变更记录](../changes/2026-10-26-343-n10-spawn-geometry.md)。

修复后 `bash tools/project.sh test` 通过 405 项 unittest、navigation-adapter integration 和 official-policy ROS probe。日志 SHA-256：`9e183c3e0043a5c9b17b198a1f9291562aa21cdafbd997d08f2568e5cd4a3f4b`，归档于 `artifacts/runs/n10-20261026-343-preflight/project-test-r01.log`。`git diff --check` 通过；无活动的本项目容器。

## 输入哈希

| 输入 | SHA-256 |
|---|---|
| `config/components/simulation/n10_long_range_spawn_minus8.json` | `b2534428e59c4b953e49f08a759b5cda8f1f0ea40f3a7d764923a797ff6f4aa2` |
| `config/runtime.json`（原全局起点 −6.5 m） | `1ddd6838ae2a678f89547ce90eea849582edcc29cddab341667bd2d1d9d3e360` |
| `config/components/mapping/n10_horizon2_speed031_calibration.json` | `33864323ae310e47d2d268b6ad091037c438a5aeb66bf4b8adcd4b7e3cbf64e0` |
| `config/components/mapping/ego_planner.json` | `077f7711b70d04c1c41e191c4518d18fcaf5d962871bb34ce33db02420b14337` |
| `config/components/navigation/n10_long_range_vio_calibration_goal.json` | `d1e73365f0cc12d4f30a5445fa25ed54e35267eb2ff80a788c5f3d7162212821` |
| `config/components/navigation/vehicle_envelope.json` | `2c76dc3e91aee1065e1f7095c29f93cb1bb79bdcaefd019ecfa333ff2a902d7c` |
| `config/components/navigation/task_supervisor.json` | `2ebcc06d25a6f550725161d3542915c29989a912ef1d6c8d48e596873980bb56` |
| `simulation/worlds/ego.sdf` | `b954336dd36f2fdd349ef953e4a6ed69c34caa90820bca3ddbfbe78bcc28213e` |
| `simulation/models/x500_d435i/model.sdf` | `1e2598053ab427833d9ebe232356a0326d00bf7c1c1fa0d3664f9ec23f55b40b` |
| `tools/project.sh` | `2be7f68c2b0cb2f5c8ac0736f8a95f757235b867844dc576ff00cf7de1c13f7b` |
| `tools/sim_runtime.sh` | `6aea8608e696c6a5baf818a90dfeecb6c5e9049da84eb4fb8d1050fd5ae616c2` |
| `tools/resolve_sim_spawn.py` | `8d1c1a513d2dd831f6152f4df7e433bbc62deaf09dbb6ddd53cd4cb1d20e52e7` |
| `tools/test_resolve_sim_spawn.py` | `2a1a6fc9eac9f547205df7a0586bac16fbe37cfe398e335517f5264132b49721` |
| `tools/n09_runtime.sh` | `7db94d809ca887b5f829169efaa473d2b1cdd0c059189ca48f240183b4db45a3` |
| `tools/run_vio_ego_flight.py` | `a5d0794130dcff8a44405db6bde94a0d378fde43a7b407fbe7a766b9cbcbea6d` |
| `tools/speed_guard.py` | `d3e3227407da9c391dad0d564bddd4b621decf56586aa416da0265b396f72da2` |
| EGO patch `0051-n10-spline-reallocation-ratio-sentinel.patch` | `b41440d75badb304fc59684718a4b2fe9a295d1fc13485c43ee0900161f8b4d1` |

Run ID：`n10-20261026-343-speed031-start8-r01`。只有一次完整 PX4/任务实验；飞行后不允许同参数重试。该协议不是飞行结果报告；运行结果单独登记。
