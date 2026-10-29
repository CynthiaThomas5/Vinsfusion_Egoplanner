# N08.2x #234：后向观察完成，但 N05 起降入口仍有 unknown

## 结果

新增 profile `n08_overhead_rear_facing_view` 完成 19/19 stages，包含 yaw −π/2→−π 后向视角和分段回中。扫描后的 N05 online/offline admission 仍一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；因此没有启动 compute-only，未产生 EGO 曲线，也没有 XY 或制动数据。

同图 N05 unknown-volume audit 重放了原始 entry query：ground plane 拟合有效（z=−0.35 m），N05 HOLD 1/1 样本通过且 0 unknown；TAKEOFF_CONTACT 有 33 unknown，ASCENT 和 DESCENT 各有 15/19 拒绝，LANDING_CONTACT 也有 33 unknown。33 个未知 cell centers 位于 map ENU `X=-1.15…-1.05 m, Y=-0.25…+0.45 m, Z=-0.15…+0.15 m`，在已确认 ground plane 以上。故拒绝原因是机体起降接触包络中的未观测体素，不是地下格或 ground-plane fit 失败。

## 运行与末态

- Run：`n08-20261024-234-rear-hold-coverage-01`；profile 19/19 stages 完成，yaw −π 与返程 −π/2 视角均实际到达。
- before/after/post-release N05 online/offline 结果一致；before 与 after 均拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。Epoch/map：`ecad083e77aa4d6c9eb59b71c753ca74` / `ecad083e77aa4d6c9eb59b71c753ca74-89eebcbecf7249769fa443089f8a5aa5`。
- fixture helper 仍报告 `localization changed or became invalid during physical scan`，原样保留；但扫描阶段完成、最终 LocalizationStatus valid、fixture detach/model absent、fresh landed detector 与 `safety_cleanup.verified_landed=true` 均有证据。车辆 DISARMED、bridge DISABLED、landed。
- 因 post-release gate 拒绝，mission 未启动。`bash tools/project.sh stop` exit 0，container `Exited (0)`，无本 run 进程。
- profile 静态检查：`python3 -m unittest tools.test_preflight_scan` 29 项通过；JSON 解析、shell syntax、`project_status.py`、`git diff --check` 均通过。

## 结论与下一项

单独水平后向视角不足以让 N05 起降包络全知。下一步围绕同一后向缺失体素，在 yaw −π 增加一次 pitch +0.45 的下视深度观测，其他 overhead/ground 阶段和所有门限保持不变；fresh N05 gate 通过前不运行 compute-only。任何后续 N08 XY 仍必须等保守停车包络通过。

详细分阶段拒绝计数、33 个 unknown cell centers、原始地图与 SHA-256 见同目录 JSON 和 `artifacts/runs/n08-20261024-234-rear-hold-coverage-01/`。
