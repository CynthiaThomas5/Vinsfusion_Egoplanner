# N08.2u #231：短走廊 compute-only 与起点 hold 复核

## 结果

compute-only runner、轨迹生成、取消后 bridge hold 和最终 landed/disarmed 均通过；N05 current-area online/offline admission 对同一 epoch/map 接受。真实 READY B-spline 与同身份地图已捕获，地图年龄满足 0.4 s 限制，连续曲线的 21 个覆盖查询均为 free。

几何证书未通过：起点 body sphere free，但半径 0.980618 m 的起点 hold sphere 含 209 个 unknown；目标 body、目标 terminal-hold 与曲线 sweep 均 free。证书因此保持 `n08_execute_authorized=false`、`stopping_envelope_proven=false`。没有执行 XY，也没有响应延迟、减速度或停车距离测量。

## 运行与安全状态

- Run：`n08-20261024-231-short-corridor-compute-01`；目标相对释放位置 `[+0.10,+0.25,0] m`，实际目标 `[0.60172,0.03123,0.97489] m`。
- N05 scan profile 完成 19/19 stages，fixture 已 detach 并从场景移除，最终 landed。fixture helper 的错误 `localization changed or became invalid during physical scan` 和退出码 2 原样保留；不能把它改写成扫描 helper 通过。独立 post-release/current-area online/offline admission 接受，identity 相同。
- Epoch/map：`c7b5560671bf4956ba382da424588479` / `c7b5560671bf4956ba382da424588479-74f5b337d6494269a36e6e375f9650e5`。
- 只读 preflight 通过 40.004 s，optimized-odometry 最大 receipt gap 87.3 ms，guard overrun 0。Mission 记录 `PASS`、READY curve、cancel accepted、cancel 后 hold 确认、0 clock regression、landed/disarmed；bridge 输入与 EGO 输出隔离，没有 EGO XY 指令送达 PX4。
- 容器按 `tools/project.sh stop` 停止，退出码 0；最终容器 `Exited (0)`，无本 run 仿真进程。

## 曲线与地图证书

| 指标 | 结果 |
| --- | --- |
| compute-only evaluator | `passed=true`；这只证明计算、取消、hold 与落地链路，`n08_exit_satisfied=false` |
| curve certificate | 未通过；`geometry_pass=false`，`map_freshness_pass=true` |
| derivative-hull vector speed bound | 0.09070 m/s；dense peak 0.09034 m/s，低于证书的 0.15 m/s 向量上限 |
| start body sphere | free，0 unknown |
| start hold sphere | unknown，209 cells |
| end body / terminal hold | 均 free，0 unknown |
| curve sweep | 21/21 free queries，cover radius 0.74275 m |
| map age | fusion 44 ms，depth source 144 ms（freshness limit 400 ms） |
| execute / stop envelope | 均未授权／未证明 |

209 个 unknown cell center 位于起点局部 ENU 的相对 `Y=-0.93…-0.83 m` 薄层（`X=-0.55…+0.55 m`、`Z=-0.63…+0.57 m`）。这是从同 run raw map 与证书 query 复算的方向性诊断，不代表这些体素是障碍，也不改变 unknown 必须拒绝的规则。它说明 #231 的正侧观察没有补齐起点 hold 球的负 Y 一侧。

速度边界也有一项需在执行前澄清：运行配置中的 per-axis `max_vel=0.075 m/s`，而证书当前 `speed_pass` 实际只比较 0.15 m/s vector cap；捕获曲线 derivative control hull 的 Y 分量为 0.08157 m/s。因此本报告只记录 evaluator 的 vector-cap 结果，不能把它表述成 per-axis 0.075 m/s 已验证。

## 证据与复现

- 原始数据：`artifacts/runs/n08-20261024-231-short-corridor-compute-01/`，重点为 `flight.json`、`n05-run-summary.json`、`preflight.json`、`n08-live-curve-map.json/.npz`、`n08-compute-only-evaluation.json` 与 `n08-curve-certificate.json`。
- 结构化结果和源文件哈希见同名 `.json` 报告。
- 运行命令：
  - `N05_KEEP_SIM=1 D435I_N08_MODE=compute_only D435I_PLANNER_CONFIG=config/components/mapping/n08_low_speed_vector_cap.json bash tools/run_n05_preflight_layout.sh n08-20261024-231-short-corridor-compute-01 n08_overhead_calibration n08_overhead_positive_side_view`
  - `bash tools/project.sh mission n08-20261024-231-short-corridor-compute-01 config/components/navigation/n08_compute_only_short_corridor_goal.json`
  - `bash tools/project.sh stop n08-20261024-231-short-corridor-compute-01`（exit 0）

## 下一子项

N08.2v #232 固定目标、场景、速度配置和释放位姿，仅把 N05 观察 profile 从 `n08_overhead_positive_side_view` 改为已有的 `n08_overhead_rear_one_side_view`（yaw −π/2 侧向观察），再运行同一 compute-only 目标。假设是额外负 Y 观测会消除 start-hold 薄层 unknown；判据是新鲜同 identity 地图上的完整 body/hold/曲线/停止走廊证书，不改变 query 半径或 unknown 语义。仍禁止 XY；同时复核 per-axis 速度限值和 evaluator 判据。
