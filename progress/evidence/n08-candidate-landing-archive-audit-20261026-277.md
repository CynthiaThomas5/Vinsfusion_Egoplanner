# N08 候选落地区历史 raw-map 回放（#277）

范围：只复核候选未来落地位置的 raw-map 几何；不构成飞行、真实触地或 N08 通过证据。输入、逐阶段计数和哈希见[机器报告](n08-candidate-landing-archive-audit-20261026-277.json)。

使用 N05 home raw-ground plane 估计 IMU 离地高度，在每张独立 raw occupancy map 上重新拟合候选地面，然后按同一 N05 体素／机体规则扫描 1 m hold、19 个下降点和末端候选触地点。3 张地图均通过；每个 phase 的 unknown 与 occupied 计数均为 0。证书明确 `ground_confirmed=false`，从未把未来落地位置伪装成已触地状态。

| 来源运行 | 使用地图 | raw-ground 支持体素 | 结果 |
| --- | --- | ---: | --- |
| #260 | 起飞后、目标前 airborne map | 231 | `candidate_landing_volume_known_and_clear` |
| #267 | 起飞后、目标前 airborne map | 122 | `candidate_landing_volume_known_and_clear` |
| #273 | 去程后 pre-turn map | 308 | `candidate_landing_volume_known_and_clear` |

此回放支持在正式 run 中先用 airborne map 预检，再在到达／保持后用新的同身份地图复检；正式降落仍须观察 bridge `LANDED` 且 PX4 disarmed。历史地图不是当前 run 的地图，不能替代每轮 fresh gate 或最终落地。

命令：`PYTHONPATH=tools python3 tools/diagnostics/audit_n08_candidate_landing_archives.py --output progress/evidence/n08-candidate-landing-archive-audit-20261026-277.json`。
