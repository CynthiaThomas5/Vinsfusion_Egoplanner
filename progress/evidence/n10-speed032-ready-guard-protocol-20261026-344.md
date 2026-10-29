# #344 N10.3：0.32 m/s planner 候选与原速度 guard 诊断协议

状态：**执行前冻结**。基于 #343 最终样条的实测控制点导数，判别 planner feasibility 与既有实际速度 guard 是否形成独立约束。本 run 不是 N11–N16 正式次数。

## 假设与唯一变量

#343 在 spawn x=−8.0 m 时，EGO 完成 10 次 replan；末轮最大 `|vx|=0.326505 m/s`，加速度门通过。配置 `max_velocity=0.31` 的 5% tolerance gate 是 0.3255 m/s，末轮超 0.001005 m/s。反算此单样本最低可行配置为 0.326505/1.05≈0.310957 m/s。

唯一主变量：N10 planner `max_velocity_m_s` 从 #343 的 0.31 改为 0.32 m/s/axis。相同曲线的 5% gate 将为 0.336 m/s，比 #343 末轮测值高 0.009495 m/s。选用 0.32 留出测量余量；它只影响 planner 接受曲线的可行性门，不表示 PX4 实际或获准速度。

## 固定项与保护

- spawn profile 固定 `[-8.0,0,0.3,0,0,0]`，单 D435i、相同 EGO 世界、16.0 m X / +0.10 m Z / +0.20 rad yaw goal、2 m planning horizon、0.25 m/s²/axis acceleration、0.730617917 m inflation 和 `official_ego` 碰撞策略均不变。
- 原独立 0.12 m/s 三维向量速度 guard 完全保持不变，仍同时监视 READY/COMPLETED EGO 参考和 PX4 local velocity。无效样本 fail-closed；参考或实测越限即取消并走现有 stop/bridge-owned landing。
- 不放宽速度、健康、地图时效、碰撞、接触或终态阈值，不改 EGO 源码，不使用真值在线控制。

## 判据与停止

一次 fresh PX4/SITL run。成功生成与目标同身份的 READY 曲线后，记录首条及完整可得的参考速度；任何参考超过 0.12 m/s 都应由守门器取消，随后确认安全停止/落地。若未触发 guard且完整到达，则还须满足独立 3 s 到达驻留、600 sim-s ACTIVE hold、定位/map/时效/接触指标及 PX4 landed/disarmed 终态，才支持该 run 的长程校准部分。planner 再次拒绝、speed guard、其他门失败或数据不足均完整保留，不通过重跑同一配置或提高门限解决。

即使曲线被接受，控制点导数也不是实际飞行速度；0.12 m/s guard 才是这次任务的既有操作上限。该实验只用于判别 planner feasibility 和 guard 响应，不授予更高飞行速度资格。

## 运行命令

```bash
D435I_N08_MODE=execute \
D435I_N09_CONTACTS=1 \
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon2_speed032_calibration.json \
D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json \
bash tools/project.sh sim n10-20261026-344-speed032-ready-guard

docker exec d435i-n10-20261026-344-speed032-ready-guard \
  bash /workspace/tools/n09_runtime.sh \
  n10-20261026-344-speed032-ready-guard \
  config/components/navigation/n10_long_range_vio_calibration_goal.json \
  n10_calibration
```

任务结束后独立读回 PX4 disarmed/landed 和 bridge LANDED/control disabled，再仅停止本项目容器。

## 运行前验证

`bash tools/project.sh test` 通过 405 项 unittest、navigation-adapter integration 和 official-policy ROS probe。日志 SHA-256：`941e15eeb5b86b9865d0c0f45bbe51668c56b394d5751489a999db50c2cbd252`，归档于 `artifacts/runs/n10-20261026-344-preflight/project-test.log`。`.31` 与 `.32` planner profile 的其余所有运行字段完全一致；`git diff --check` 通过。#343 的前置失败和正式结果均保留，当前无活动项目容器。

## 固定输入哈希

| 输入 | SHA-256 |
|---|---|
| `config/components/mapping/n10_horizon2_speed032_calibration.json` | `b11efc421a54a5566444d81c0d1a01bbfef1435cae8392c5d803a7b813892a37` |
| `config/components/mapping/n10_horizon2_speed031_calibration.json` | `33864323ae310e47d2d268b6ad091037c438a5aeb66bf4b8adcd4b7e3cbf64e0` |
| `config/components/simulation/n10_long_range_spawn_minus8.json` | `b2534428e59c4b953e49f08a759b5cda8f1f0ea40f3a7d764923a797ff6f4aa2` |
| `config/runtime.json` | `1ddd6838ae2a678f89547ce90eea849582edcc29cddab341667bd2d1d9d3e360` |
| `config/components/navigation/n10_long_range_vio_calibration_goal.json` | `d1e73365f0cc12d4f30a5445fa25ed54e35267eb2ff80a788c5f3d7162212821` |
| `config/components/navigation/vehicle_envelope.json` | `2c76dc3e91aee1065e1f7095c29f93cb1bb79bdcaefd019ecfa333ff2a902d7c` |
| `config/components/navigation/task_supervisor.json` | `2ebcc06d25a6f550725161d3542915c29989a912ef1d6c8d48e596873980bb56` |
| `config/components/mapping/ego_planner.json` | `077f7711b70d04c1c41e191c4518d18fcaf5d962871bb34ce33db02420b14337` |
| `tools/project.sh` | `2be7f68c2b0cb2f5c8ac0736f8a95f757235b867844dc576ff00cf7de1c13f7b` |
| `tools/sim_runtime.sh` | `6aea8608e696c6a5baf818a90dfeecb6c5e9049da84eb4fb8d1050fd5ae616c2` |
| `tools/n09_runtime.sh` | `7db94d809ca887b5f829169efaa473d2b1cdd0c059189ca48f240183b4db45a3` |
| `tools/run_vio_ego_flight.py` | `a5d0794130dcff8a44405db6bde94a0d378fde43a7b407fbe7a766b9cbcbea6d` |
| `tools/speed_guard.py` | `d3e3227407da9c391dad0d564bddd4b621decf56586aa416da0265b396f72da2` |
| EGO patch `0051-n10-spline-reallocation-ratio-sentinel.patch` | `b41440d75badb304fc59684718a4b2fe9a295d1fc13485c43ee0900161f8b4d1` |

Run ID：`n10-20261026-344-speed032-ready-guard`。该协议是执行前约束；结果另行登记。
