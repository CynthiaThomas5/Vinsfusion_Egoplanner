# N08.2w #233：隔离负侧观察通过 N05，但 EGO 未形成 READY 曲线

## 结果

新增的 16 阶段 `n08_overhead_negative_side_view` 完整执行，实际到达 yaw −π/2、pitch 0。支架扫描后的 N05 after/post-release/current-area online/offline admission 均以同一 epoch/map 接受；mission preflight 通过。

随后同一仿真中的 compute-only action 被 EGO 以 `planner_full_curve_unknown` 中止，没有生成 B-spline 或 READY PositionCommand。失败后采集到同 identity raw map。按配置目标 offset 反推的 start body sphere 有 36 unknown、start hold sphere 有 394 unknown、goal terminal-hold 有 472 unknown；直线 production-mirror 的第一条覆盖查询含 38 unknown。这里没有 B-spline，直线复算只用于定位未知区域，不是 EGO 精确曲线证书。XY 未执行，响应延迟、最小可用减速度、实际停止距离和跟踪误差都未测；N08 仍未通过。

## N05 支架结果与安全状态

- Run：`n08-20261024-233-isolated-negative-side-compute-01`；profile `n08_overhead_negative_side_view`，16/16 stages。
- before-scan online/offline N05 gate 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；after-scan、post-release、mission current-area gates 均为 `all_entry_phases_known_and_clear`，online/offline 一致。
- Epoch/map：`609f5fa6f7b348e29093738c60b822b5` / `609f5fa6f7b348e29093738c60b822b5-4c9ed6561c214ec4b5c050dfae1bf6ac`。
- fixture helper 最后读回报 `fresh DISARMED status is required for every fixture command`，helper exit 2；原错误保留。独立结果记录 attached→detached、fixture model absent、final landed，post-release gate 读回 DISARMED/landed。helper 的 `safety_cleanup.verified_landed` 未置 true，所以 runner 留下 `n05-monitor-required.txt`。之后 mission 完成并记录 `landed_and_disarmed=true`，当前 N05 online/offline gate 仍通过；据这些独立读回写入 `n05-monitor-resolution.json`，再清除过期监护标记。仿真按 `tools/project.sh stop` 停止，exit 0，container `Exited (0)`，没有本 run 进程。
- read-only preflight 通过 40.008 s，optimized-odometry 最大 receipt gap 83.8 ms，guard overrun 0。Mission 的 N05 current-area same-identity online/offline gate 通过。

## Same-identity map 查询

mission 目标为 `[-0.21877,0.14184,0.93923] m`；按配置 `[+0.10,+0.25,0] m` offset 反推 start 为 `[-0.31877,-0.10816,0.93923] m`。后验失败 map 与 N05 post-release snapshot identity 一致；两份 snapshot 对下列查询给出相同结果：

| 查询 | 结果 |
| --- | --- |
| start body，半径 0.730618 m | unknown，36 cells |
| start hold，半径 0.980618 m | unknown，394 cells |
| goal body，半径 0.730618 m | free，0 unknown |
| goal terminal hold，半径 0.980618 m | unknown，472 cells |
| production-mirror straight-line sweep | 第 1 个查询即 unknown，38 cells；cover radius 0.742857 m |

起点 hold 的 394 个 unknown cell center 全位于相对 `X=-0.931…-0.731 m`，质心 `[-0.804,-0.006,0.005] m`；目标 hold unknown 主要在后方与 +Y 侧。它们位于 ground plane `z=-0.35 m` 以上。这个 run 的缺失方向与 #231 的 map 诊断不同；不同 fresh epoch 的 ENU 坐标不能直接当成同一空间扇区比较。当前结论只使用 #233 自己的 start/goal 与 same-run map。

因此负侧视角 profile 修复了 #232 未到达负侧观察阶段的问题，但没有得到可用的 EGO 曲线几何。下一项应针对同一地图显示的后向 hold unknown 设计新的 DISARMED 观察假设；仍需保留 N05 健康门、unknown 拒绝规则和几何半径，不能进入 XY。

## 变更与复核

- 新增 `n08_overhead_negative_side_view` profile，沿用原 profile 前 9 阶段，仅增加 yaw −π/2、pitch 0 单侧观察和回中；probe / shell runner allowlist 同步更新。
- `tools/test_preflight_scan.py` 增加 profile 定义和姿态序列检查。
- `python3 -m unittest tools.test_preflight_scan`：28 项通过；JSON 解析、`bash -n tools/run_n05_preflight_layout.sh`、`python3 tools/project_status.py`、`git diff --check` 均通过。结构检查只证明 profile/manifest 一致，不替代本次 SITL 结果。
- N05 与 mission 命令、原始 trace、map、证书、监护状态解析和 SHA-256 见同目录 JSON 与 `artifacts/runs/n08-20261024-233-isolated-negative-side-compute-01/`。
