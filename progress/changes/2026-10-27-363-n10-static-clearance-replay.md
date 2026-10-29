# #363 N10.3 #361 静态净空复算与障碍场景盘点

对话摘要：[2026-10-27 #363](../../collaboration/dialogues/2026-10-27-363-n10-static-clearance-replay.md)

## 改动与产物

- 只读复用 #361 的完整 PX4 SITL 轨迹、truth、实际加载 SDF 与当前 runtime 机体包络，生成 `n10-clearance-evaluation.json`。
- 证实 #361 实际运行的是 `simulation/worlds/ego.sdf` 静态障碍场景（23 个非地面碰撞形状），更正早先“无障碍物”的状态描述。
- 盘点动态障碍能力：N06 probe 可注入并评估 planner-only replacement/handoff，但没有 PX4/bridge/trajectory execution；其创建服务硬编码 sensor_calibration 世界，不能直接代表当前 PX4 中的在线重规划。
- 证据：[报告](../evidence/n10-clearance-static-world-replay-20261027-363.md)、[JSON](../evidence/n10-clearance-static-world-replay-20261027-363.json)。

## 验证

`python3 tools/debug_truth/evaluate_n10_clearance.py artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m --world-sdf artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/vio_initialization.sdf`：exit 0，样本净空0.352841m；扣除观测到的最大相邻样本包络运动后0.337908m。

限制：该结果是 SDF/真值离线静态几何测量；运动扣减不是连续动力学上界，不冻结正式净空标准。未完成动态障碍飞行重规划。父 N10 与 N10.3 保持未通过。
