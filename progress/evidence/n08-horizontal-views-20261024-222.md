# N08.2l #222：水平观察 run 失败诊断

日期：2026-10-24。父任务 N08 保持 `in_progress`。本次不是 N08 通过证据。

## 假设与判据

在 #221 顶板＋`wall_box_column` 场景和原 N05/EGO 安全门限不变时，增加固定高度 yaw=−π/2、+π/2 的水平观察，能覆盖 start 后方和 +Y 目标前方 terminal-hold 未知体素。只有完整扫描、post-release N05 online/offline gate、同图 body／terminal-hold 球及整条线段查询全部通过，才允许后续 compute-only；不允许 XY 执行。

## 结果

- Run：`n08-20261024-222-horizontal-views-01`；profile `n08_terminal_horizontal_views`，20 个阶段、500 仿真秒上限，执行约 499.4 墙钟秒。
- 初始 N05 before online/offline 结果一致，拒绝原因为 `ground_plane_insufficient_raw_occupied_voxels`。之后支架扫描开始，但未到 release gate。
- 扫描在第 14/20 阶段中止，阶段 14 是 yaw 从 −π/2 连续转向 +π/2 的 180°段。该段 trace 中 normalized cost 从 0.6266 升至最高 0.99485（机体 yaw 约 1.004 rad），随后定位健康报告 `normalized_cost_exceeded`、normalized cost 1.00967；项目阈值仍为 1.0，没有调整。raw VINS solver 记录持续到清理阶段，当前证据未显示 `telemetry_stale`。
- 180°连续转动与越线在时间上相邻，支持“长转向段造成特征／估计退化”的假设，但不能单凭本 run 证明因果；也没有完成 +Y 水平视角，因此不能判断未知格是否消失。
- `n05_live_check_completed=false`；没有 N05 after/post-release map，也没有 body／terminal-hold／整条路径 raw 查询。compute-only、READY、XY 和制动均未执行。

## 安全收尾

`fixture-result.json` 记录 `ARMING_STATE_DISARMED`（枚举值 1）、fresh landed 读回（收据年龄约 0.36 s）、支架已 detach 且模型不存在，无 ROS 控制／goal publisher。保留仿真经 `bash tools/project.sh stop n08-20261024-222-horizontal-views-01` 停止，容器 exit 0。

## 下一步

新增 #223 profile：左右两次 90°观察之间回到 yaw=0 并短暂停留，其他场景、视角停留时间、N05/EGO 门限和速度不变。该实验检验“中立方向重获视觉特征”是否避免 180°连续转向时的健康越线。仍须满足同图所有准入查询，任何未知都继续 fail-closed。

原始运行目录：`artifacts/runs/n08-20261024-222-horizontal-views-01/`。

| 文件 | SHA-256 |
| --- | --- |
| `n05-run-inputs.json` | `ba9cfe5d28de133e922b5dcbd1ddbbfcacfcd4ad278213fdf533e5e748912304` |
| `fixture-result.json` | `ed26c42947aae1c38cbbe2cfbae72da44028a789649cdfcbcc52036b77366fa8` |
| `fixture-trace.jsonl` | `db3cb4c83b60e1519062aba5b3ce1727a2524f5a690e2d1061597ce3e46317b7` |
| `fixture-vins.jsonl` | `59d8cf9a15571edf06ca5be7d04427572c8f32863051dd8a804ac8ad8ecd04ae` |
| `n05-before/n05-live-entry-check.json` | `e5371ccde2cf286496da7f917355755b5daefac83fdf5662d7e513641dd852b1` |
| `n05-before/n05-offline-entry-replay.json` | `974185fafec008948db94414aebf31869967f02b58600bdf8894ec670b0bada9` |
