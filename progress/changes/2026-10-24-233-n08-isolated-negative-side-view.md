# N08.2w #233：隔离的负 Y 水平视角

## 问题与假设

#232 的现有 `n08_overhead_rear_one_side_view` profile 在负 Y 水平观察前，先执行 yaw +π/2、pitch −0.45；在这个阶段 scan 中止，负 Y 观察未到达。假设是保留已完成的 overhead/ground-observation 段，只换成一次 yaw −π/2、pitch 0 水平视角并回中，可以避免前置姿态对定位的影响，同时观察 #231 起点 hold 球缺失的负 Y 薄层。

## 唯一变量与允许范围

- 唯一主要变量：侧向观测姿态段，从先行 `(+π/2, −0.45)`/多侧 profile 改为单独 `(-π/2, 0)` 后回中。
- 保持 overhead scan 的前 9 个阶段、布局、release/spawn pose、目标 `[+0.10,+0.25,0] m`、速度配置、几何半径、健康门限与 PX4 参数不变。
- 实现只增加 N05 scan profile 和 runner allowlist，不改 planner、安全门限或飞行控制。
- Run ID：`n08-20261024-233-isolated-negative-side-compute-01`。

## 产物与验收

新增的 profile 必须通过项目 profile validation；只有 fresh N05 post-release/current-area online/offline 同 identity admission、preflight 和定位健康均通过时，才运行同一 bridge-isolated compute-only 目标。记录 READY curve、same-identity raw map 和 start/body/hold/full-curve/0.50 m stop-corridor 几何。N05 admission 不通过就不发目标。任何结果都不执行 XY；即使 map certificate 通过，N08 的动态停止包络仍需后续独立量测。

## 实际结果

- 新 profile 静态校验通过：`python3 -m unittest tools.test_preflight_scan` 28 项通过；JSON parse、`bash -n tools/run_n05_preflight_layout.sh`、`python3 tools/project_status.py` 和 `git diff --check` 均通过。
- N05 16/16 stages 完成；yaw −π/2、pitch 0 视角实际执行，after/post-release gates 同 identity 通过。helper 的最终 fresh-DISARMED-status error 保留；独立 fixture removal、N05 gates 和 mission landed/disarmed 回读后清除 monitor marker，详情见 `n05-monitor-resolution.json`。
- Mission preflight/current-area gate 通过；compute-only 在 B-spline 前以 `planner_full_curve_unknown` 拒绝，未生成 READY 或 PositionCommand。相同 map 上 start body 36 unknown、start hold 394 unknown、goal terminal-hold 472 unknown；无 XY／制动测量。
- Mission 返回 exit 2（预期保留 fail-closed 结果）；`tools/project.sh stop` exit 0，container exit 0。详细结果与 SHA-256 见 [#233 report](../evidence/n08-isolated-negative-side-view-20261024-233.md) 与同名 JSON。

## 下一子项

N08.2x #234 保留相同 overhead/ground stages 和健康/几何门限，沿 #233 已通过的 yaw −π/2 方向继续转至 yaw −π、pitch 0，再回中；检查后向 unknown 是否被观察。仅 DISARMED N05；fresh admission 不过不启动 compute-only，任何结果不执行 XY。
