# N08.2l #222：补足 start/goal terminal-hold 的水平视角

## 假设、唯一变量与判据

- 同一顶板布局 #221 已让 0.730618 m body spheres 全 free，但 0.980618 m terminal-hold query 的未知格位于 start 后方 y≈−1.05 m 和 +Y0.6 goal 前方 y=1.25–1.45 m。
- 假设在固定 N05 支架位姿 x=0、z=1.0 m 增加 yaw=−π/2 与 +π/2、pitch=0 水平视角，可给这两个格区补充深度 rays；顶板、box/column、support route 和所有 safety threshold 不变。
- 判据：同 run N05 after/post-release/current-area gate online/offline 通过；原 production 半径 start、goal body、start/goal terminal-hold spheres 和完整候选线 sweep 均全 free，顶板表面仍 raw occupied。未满足则不启动 compute-only；无停止边界前不执行 XY。

## 允许范围与产物

- 新增 `n08_terminal_horizontal_views` 支架 profile；只在 home hold 的 yaw 观测顺序增加两侧水平视角及中立回归，不修改 PX4、定位、N05/N06/EGO 几何／门限、unknown 策略、目标或速度。
- run：`artifacts/runs/n08-20261024-222-horizontal-views-01/`；证据 `progress/evidence/n08-horizontal-views-20261024-222.{md,json}`。
- 若所有 raw gates 通过，后继 #223 在同一 runtime 执行 bridge-input-isolated compute-only，记录 exact READY/abort/cancel/action-time state；仍不执行 XY。
- 若地图仍 unknown，按 exact voxel location 选择新的可观测性动作；不重复 N07，不把 support or structure checks 算 N08 pass。

## 实际结果

- 20 阶段 profile 执行到第 14 阶段；在 yaw −π/2→+π/2 的连续转动期间，localization 因 `normalized_cost_exceeded` 中止（1.00967，现有上限 1.0）。VINS raw solve 记录仍持续到清理时段；当前没有证据把失败归为 telemetry stale。
- 在线／离线初始 N05 gate 相同拒绝 `ground_plane_insufficient_raw_occupied_voxels`；未到 N05 after/post-release 阶段，因此无扫描后地图和 raw sphere/path 结论。compute-only、XY 均未启动。
- 安全清理确认 DISARMED、landed、fixture detached／模型移除；容器由 `bash tools/project.sh stop ...` 停止并 exit 0。
- 最高 scan-trace cost 为 0.99485，位于 yaw 约 1.004 rad；随后 health 读回 1.00967 越过固定门限。连续 180°段与失败相邻，但因果未证实。具体证据和哈希见 [#222 报告](../evidence/n08-horizontal-views-20261024-222.md)。
- 下一子项 #223 保持布局、门限和观察停留不变，只在两个 90°水平视角之间回到 yaw=0 并停留，以检验中立方向重获特征是否避免 cost 越线。
