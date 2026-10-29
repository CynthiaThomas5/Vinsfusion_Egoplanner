# N08.2s #229：单侧后方观察未解除曲线 unknown

日期：2026-10-24。N08 保持 `in_progress`。本项仅测试 −π/2 单侧支架观察并诊断 fresh raw map；没有水平轨迹执行或制动测量。

## 支架扫描与健康

- Run：`n08-20261024-229-one-sided-rear-view-01`，profile `n08_overhead_rear_one_side_view`，完成 19/19 stages。扫描前 online/offline N05 gate 都因 `ground_plane_insufficient_raw_occupied_voxels` 拒绝；扫描后 `after`、`post-release`、mission current-area online/offline gate 均以同一 epoch/map `d8c64e91249a491788c439dc1dffb4e3`／`...-adf5b7f22e964d888f6a5b03da98ddf2` 接受。
- fixture helper 报 `localization changed or became invalid during physical scan`，exit 1；该失败保留。它同时记录完成 19 stages、attached→detached、fixture model removed、最终 landed。post-release 和 current-area 检查重新读回 localization valid、bridge DISABLED、DISARMED、landed；不将 helper 失败改写成 pass。
- mission preflight 通过 40.015 s 只读窗口，最大 optimized-odometry receipt gap 84.3 ms，未越过 guard。之后 33.4 s observer 时间线记录 27,423 个事件；754/754 LocalizationStatus valid 且 `fresh_inputs_and_usable_solver`，164/164 MapStatus 为 `ready`。没有复现 telemetry stale。MapStatus source-stamp 最大间隔为 428 ms；记录为时序观察，不改变 400 ms 门限，也不把 `ready` 扩展成制动证据。

## Compute-only 结果

runner 发出目标后，EGO 在尚未发布 B-spline 时以 `planner_full_curve_unknown` 中止。planner 日志报告完整曲线证书 36 个查询、reason=`unknown`；`trajectory_ready_seen=false`。compute-only evaluator 因 runner FAIL 而失败，未发生 cancel 后 hold 验收；PX4 最终 landed/disarmed，桥状态读回 `phase=LANDED`、`control_enabled=false`、`armed=false`、`landed=true`。桥没有订阅 EGO `/position_cmd`，没有执行水平轨迹。运行容器随后 `tools/project.sh stop` exit 0。

## 原始 unknown 定位

未取得 action-time spline/map 捕获：现有 observer 只在匹配 B-spline 后保存 raw map，故 `n08-live-curve-map.json` 明确记录 `matching_goal_epoch_bspline_not_observed`。下面的空间查询使用该 run 的 N05 post-release/current-area 同身份快照，**是任务前的地图诊断，不冒充 action-time 曲线证书**。post-release 与 current-area raw archive 字节哈希一致：`6e1a25d29107e5e0a0316b4ba4def7d9960db339a68632cf5d96716cd43f2853`。

用 `run_n08_compute_only.py` 实际 target 与固定 `[0.5,0.2,0] m` offset 还原起点，再从 `tools/probe_n06_live_layout.py` 提取 production-mirror `raw_sphere_query`／`raw_line_sweep` 函数复算：

| 查询 | 结果 |
| --- | --- |
| 起点 body sphere，半径 0.730618 m | free，0 unknown |
| 起点 hold sphere，半径 0.980618 m | unknown，209 cells |
| 目标 body sphere，半径 0.730618 m | free，0 unknown |
| 目标 terminal-hold sphere，半径 0.980618 m | unknown，254 cells |
| 起点至目标连续直线扫掠 | 22 个查询中前 21 个 free；末查询 unknown 6 cells，中心 `[0.4049, 0.0620, 0.9628] m` |

planner 在 action-time 记录的 36-query 曲线拒绝与上述地图诊断相符，但因没有 action-time raw map，不能断言两者完全同一批失败体素。起点 hold sphere 的未知 voxel center 方向统计为：167/209 位于机头反向扇区（相对 yaw >135°），另有 30 个前侧向、12 个后侧向。目标 terminal-hold unknown 的 voxel center 位于 `y=0.85…1.05 m`，相对机头主要在两侧向扇区（113、141）。这些未观测格的中心高度为 0.35…1.65 m；测得 ground plane 为 z=−0.35 m，缺失空间在地面上方，不是地下格。

因此 −π/2 视角没有解除目标侧 unknown，EGO 正确 fail-closed。下一次只测试 +π/2 单侧水平视角：保持同一 overhead profile、场景与全部门限，省略 −π/2 和第二侧转向；并让只读 observer 在 goal 失败但无 B-spline 时也抓取同身份 map，以取得 action-time 诊断。无论 compute-only 结果如何，停止边界未证明前都不执行 XY。

## 证据文件

原始产物：`artifacts/runs/n08-20261024-229-one-sided-rear-view-01/`。该 run 的 N05 raw map 与事件、flight／planner 结果由下表哈希固定；offline-query 计算使用已保存 NPZ 和源码中的 production-mirror 查询实现。

| 文件 | SHA-256 |
| --- | --- |
| `fixture-result.json` | `4544da8632a45a391c58e991b0a1b9743e3d7e9186a5491abbb166366355f971` |
| `fixture-stages.json` | `d93184ef96d61f1cae18a1c21ac3609e32a29aa795f4b7984666bd64ca92f6d9` |
| `n05-run-summary.json` | `cca1632a72098541b73dd501486ef5ab9cc257d382142ac988f2c3345d640868` |
| `flight.json` | `26d5b415b65413d212999c09271ee2cc82d0d7d21762359dd204e05d509360d8` |
| `n08-compute-only-evaluation.json` | `7949b6bd7b8e35aad1141368d78c0da87199d7062e0c946c875daf34a79b2e8e` |
| `n08-localization-source-timeline.json` | `f215dab4e7fae8d48e184da3890805600526772b97554fbe34191b42914f1baf` |
| `planner-observation.json` | `9f7f6d396f04e45921d537151daab2476bbcf194bd24a4689d020cad6d612d1b` |
| `n05-post-release/n05-live-raw-map.npz` | `6e1a25d29107e5e0a0316b4ba4def7d9960db339a68632cf5d96716cd43f2853` |
| `tools/probe_n06_live_layout.py` | `8c90741621fcac95680891d7c22526810b9c84a588d7c4ab38beb1993a67a11a` |
