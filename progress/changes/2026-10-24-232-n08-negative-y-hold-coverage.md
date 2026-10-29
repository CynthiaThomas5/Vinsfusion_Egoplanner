# N08.2v #232：负 Y 侧视与起点 hold 覆盖

## 问题与假设

#231 捕获的同身份 raw map 显示，起点 hold 球 209 个 unknown cell 全落在起点相对 ENU `Y=-0.93…-0.83 m`。当前正侧 profile 未覆盖这个薄层。假设是将 N05 支架视角切换到现有 `n08_overhead_rear_one_side_view` 的 yaw −π/2 观察，可增加该方向的深度 free-ray 观测，使新的同 run hold 球查询通过。

## 唯一变量、范围与产物

- 唯一主要变量：N05 支架观察 profile 从 `n08_overhead_positive_side_view` 改为 `n08_overhead_rear_one_side_view`。
- 固定：场景 `n08_overhead_calibration`、N05 release/spawn pose、compute-only 目标 `[+0.10,+0.25,0] m`、planner 配置、EGO 参数、几何 query 半径与健康门限。
- Run ID：`n08-20261024-232-negative-y-hold-compute-01`。
- 产物：fresh N05 online/offline gate、定位/地图时间线、compute-only runner、same-run READY spline/map、完整 curve/hold/stop-corridor 复核、落地和清理状态。

## 验收与运行边界

先完成 DISARMED N05 支架扫描。只有 post-release/current-area 同 identity admission 和 mission preflight 通过时才启动 bridge-isolated compute-only。检查 start/body/hold、goal/body/terminal hold、整条 curve 和目标后 0.50 m stop corridor。保留 `unknown` 拒绝语义，不修改 query 半径、健康门限或速度配置。不得执行 XY；即便几何通过，停止包络仍须实测延迟与可用最小减速度后才可审查 execute。另记录 #231 发现的速度审查缺口：certificate 的 vector-cap 与配置 per-axis limit 不一致。

## 实际结果

- scan 前 online/offline admission 同步拒绝 `ground_plane_insufficient_raw_occupied_voxels`；车辆 landed、DISARMED、bridge DISABLED。
- `n08_overhead_rear_one_side_view` 实际在 stage 9–10 先到 yaw +π/2、pitch −0.45，stage 12–13 才到 yaw −π/2。helper 在 stage 9 执行中检测到 localization 失效，completed 9/19，末态 `normalized_cost_exceeded`、cost 1.702。负 Y 水平观察没有执行；trace 最后仍为 valid、cost 0.527，未捕获随后变为失效的确切时刻。
- fixture detach/remove 与最终 landed 有证据；`n05-fixture.exitcode=1`，外层 runner exit 12。post-release/current-area gate 和 compute-only 均未启动。
- `tools/project.sh stop` exit 0，容器退出且无本 run 进程。无 XY、无制动数据。
- 详细结果与 source/artifact SHA-256 见 [#232 report](../evidence/n08-negative-y-hold-coverage-20261024-232.md) 与同名 JSON。

## 下一子项

N08.2w #233 为此前 profile 创建独立负 Y 水平观察：保留 overhead/ground scan 阶段，只用 yaw −π/2、pitch 0 视角替换先行的 yaw +π/2、pitch −0.45 观察，再回中。先做 DISARMED N05；只有 post-release/current-area gate 通过才进入相同 compute-only 目标。仍不执行 XY。
