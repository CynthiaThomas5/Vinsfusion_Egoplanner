# N08.2u #231：同起点短目标与停止走廊复核

## 假设与唯一变量

#230 失败态同身份 raw map 的 production-mirror 查询显示，原 `[0.5,0.2,0] m` 目标在起点附近首先命中 unknown。保持场景、spawn/release pose、N05 支架 profile、规划速度和所有门限不变，仅将 compute-only 目标 offset 改为 `[0.1,0.25,0] m`。该 offset 在 #230 raw map 上形成 0.269 m 路径；路径目标 hold 与目标后 0.50 m swept corridor 的查询均 free。起点 0.980618 m hold sphere 仍有 309 unknown，故这是待 fresh-map 检查的候选，不是通过证书。

## 产物

- `config/components/navigation/n08_compute_only_short_corridor_goal.json`：单目标 compute-only profile。
- fresh N05 同 identity gate、source timeline、planner/action 结果、失败或成功态 same-goal/map capture 和曲线证书。
- 原 N05/定位/速度门限不变；不修改 N07 已通过记录。

## 验收与运行边界

post-release/current-area online/offline N05 gate 必须对同一 epoch/map 一致通过；Mission preflight 和 localization health 必须通过；compute-only bridge 仍与 EGO `/position_cmd` 隔离。对运行期真实 READY spline 与同身份 raw map重算 start/body/hold、goal/body/hold、连续曲线及 goal 后 0.50 m stop corridor。记录目标、曲线与 PX4 设定点以后的运动采样（compute-only 不应有 EGO XY 到 bridge）。无论结果如何，stop envelope 未证明前不执行 XY；失败保留为失败证据，不放宽阈值。

## 运行计划

Run ID：`n08-20261024-231-short-corridor-compute-01`。先用 `n08_overhead_positive_side_view` 完成 fresh DISARMED N05 scan，再以 `D435I_N08_MODE=compute_only`、`config/components/mapping/n08_low_speed_vector_cap.json` 和本 profile 启动一次 mission；最后确认 bridge landed/disarmed、fixture 已移除、容器退出。

## 实际结果

- N05 19/19 stages；fixture detached、从场景移除、最终 landed。fixture helper 错误 `localization changed or became invalid during physical scan` 与 exit code 2 保留；独立 post-release/current-area online/offline admission 接受，identity 相同。
- Mission `PASS`，生成 1 条 READY spline；取消被接受，bridge hold 确认，0 clock regressions，最终 landed/disarmed。compute-only bridge 输入隔离，没有 EGO XY 指令到 PX4。
- `n08-compute-only-evaluation.json` 通过其有限范围。fresh same-identity curve certificate 未通过：map freshness 和 21/21 curve sweep 通过，body 与 terminal hold 通过，但 start hold 含 209 unknown。stop envelope / execute 仍未证明。
- Unknown 体素集中在起点局部 ENU 的相对 Y=-0.93…-0.83 m 带。另发现证书只验证 0.15 m/s 向量上限，未验证配置的 per-axis 0.075 m/s；捕获曲线 Y derivative-control bound 为 0.08157 m/s。这两项均在证据报告明确保留。
- 原始运行和逐项证据见 [#231 report](../evidence/n08-short-corridor-compute-20261024-231.md) 及同名 JSON。运行后执行 `tools/project.sh stop`，exit 0，容器退出且无本 run 进程。

## 下一子项

N08.2v #232 固定目标、场景、释放位姿、planner 和几何门限，只将 N05 观察 profile 切换为现有 `n08_overhead_rear_one_side_view`，再运行相同 compute-only 目标。检查 fresh same-identity start hold 是否清除负 Y unknown，复核曲线与停止走廊证书及 per-axis speed acceptance；仍不执行 XY。
