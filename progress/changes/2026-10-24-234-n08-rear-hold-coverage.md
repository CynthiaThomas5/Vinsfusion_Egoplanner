# N08.2x #234：后向视角与起点 hold 覆盖

## 问题与假设

#233 同身份 raw map 的 start hold sphere 有 394 unknown，全部落在起点相对 ENU `X=-0.931…-0.731 m` 后向薄层；goal hold 另有 472 unknown。#233 已证明从中立位经负侧 yaw −π/2 的支架观察可完成 N05 admission，但没有 READY 曲线。假设是沿同一方向再转 90°至 yaw −π、pitch 0，可以直接观察后向区域并降低 start-body/hold unknown。

## 唯一变量、范围与产物

- 唯一主要变量：N05 侧向观测范围从 yaw −π/2 延长到 yaw −π；返程分段经过 −π/2 与 0，避免一个 180°返回段。
- 保持 #233 前 9 个 overhead/ground scan stages、布局、release/spawn pose、目标 `[+0.10,+0.25,0] m`、planner、几何门限、健康门限及 PX4 参数不变。
- 新 profile：`n08_overhead_rear_facing_view`；Run ID：`n08-20261024-234-rear-hold-coverage-01`。
- 新增 scan config / allowlist 与 profile 单测；不改规划器、安全阈值或控制代码。

## 验收与运行边界

先运行 DISARMED N05 scan。profile 完成且 post-release/current-area online/offline admission 对同一 identity 通过后，才运行同一 bridge-isolated compute-only 目标。复核 body/hold、curve、目标后 0.50 m stop corridor；unknown 仍拒绝。若 N05 健康或安全门失败，则不提交导航目标。任何结果都不执行 XY。


## 结果与验证

- Run `n08-20261024-234-rear-hold-coverage-01` 完成 19/19 stages；yaw −π/2 与 −π 均到达。fixture helper 报 `localization changed or became invalid during physical scan`，原样保留；最终 localization valid，fixture detached／Gazebo model absent，车辆 landed、DISARMED，bridge DISABLED。
- before/after/post-release N05 online/offline 结果一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。同身份 epoch/map 为 `ecad083e77aa4d6c9eb59b71c753ca74` / `ecad083e77aa4d6c9eb59b71c753ca74-89eebcbecf7249769fa443089f8a5aa5`。
- 只读 audit 拟合 ground plane z=−0.35 m；HOLD 为 0 unknown，TAKEOFF_CONTACT 有 33 个 unknown voxel centers，范围 ENU X=−1.15…−1.05、Y=−0.25…+0.45、Z=−0.15…+0.15 m，均高于 ground plane。该拒绝在 N05 规则下有效；compute-only 未启动，没有 goal、控制或 XY。
- 结构与profile验证：`python3 -m unittest tools.test_preflight_scan` 29 tests passed；`python3 -m json.tool config/components/simulation/preflight_scan.json`、`bash -n tools/run_n05_preflight_layout.sh`、`python3 tools/project_status.py`、`git diff --check` 均通过。Run stop exit 0，无本 run 活动进程。
- Evidence: [报告](../evidence/n08-rear-hold-coverage-20261024-234.md), [JSON](../evidence/n08-rear-hold-coverage-20261024-234.json)。对话摘要：[dialogue](../../collaboration/dialogues/2026-10-24-234-n08-rear-hold-coverage.md)。

## 交接

#234 说明水平后向观察不足以填充起降 contact 体积；unknown 体素位于已确认地面上方。下一子项 N08.2y #235 在同一 yaw=−π 后向姿态增加 pitch=+0.45 rad 下视停留并返回 pitch=0；其它 19 个既有阶段、布局和门限不变。先运行 DISARMED N05 scan；post-release/current-area N05 gate 若未通过，不启动 compute-only。
