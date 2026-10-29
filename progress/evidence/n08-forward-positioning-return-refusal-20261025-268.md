#268：首条 EGO 曲线越过 5 cm 管道，安全拒绝

## 准入

全新 SITL epoch `49a861d432c7466691ea853e0066dc78`。N05 支架扫描完成 15/15；工具仍报告 `localization changed or became invalid during physical scan`，根因未明并保留。释放后及 mission current-area 在线／离线检查均接受，使用同一 epoch/map_id，N05 `diagnostic_pass=true`。40.00496 s preflight 通过；最大 optimized-odometry 回执间隔 0.39636 s，内部 guard 超限计数 1。

起飞后前向 corridor raw-map 证书通过，实际执行的第一条 EGO 目标为原定 0.6 m 前向目标。在线样条检查在动作早期拒绝轨迹，因此 #268 新增的 0.22 m 定位目标、原地转头、转头后更新融合地图和 EGO 前向返航都没有执行。

## 拒绝证据

连续曲线采样证书结果为 `sampled_curve_outside_continuous_tube_bound`：横／垂最大偏差 0.05264683 m，超过固定 0.05 m 边界 0.00264683 m；最小连续余量 −0.00264683 m。1148 个样点，最大样点间距 0.00099921 m，样点间位移上界 0.00049960 m。该结果是实际样条曲线超界，不是控制点凸包误报。

首条目标开始附近 PX4 local-position NED 垂向速度约为 +0.02304 m/s，总速度约 0.02340 m/s。#267 同一阶段的垂向速度约 +0.01970 m/s，其曲线偏差为 0.04749 m；两次结果有相关性，但不足以证明垂向残速导致曲线超界。5 cm 认证界保持不变。

本次首条动作未通过，独立制动评估缺少 `post_goal_hold_end_sim_ns`，没有新增制动测量。末态 bridge `LANDED`、`armed=false`、`landed=true`；PX4 `arming_state=1`、`landed=true`。项目容器停止后，未发现该运行容器仍在运行。

## 运行文件

- [flight.json](../../artifacts/runs/n08-20261025-268-forward-positioning-return/flight.json)
- [N05 汇总](../../artifacts/runs/n08-20261025-268-forward-positioning-return/n05-run-summary.json)
- [preflight](../../artifacts/runs/n08-20261025-268-forward-positioning-return/preflight.json)
- [独立制动评估](../../artifacts/runs/n08-20261025-268-forward-positioning-return/n08-braking-evaluation.json)
- [ground map](../../artifacts/runs/n08-20261025-268-forward-positioning-return/n08-trial-ground-map.npz) 与 [airborne map](../../artifacts/runs/n08-20261025-268-forward-positioning-return/n08-trial-airborne-map.npz)
- [launch manifest](../../artifacts/runs/n08-20261025-268-forward-positioning-return-stack/launch-manifest.json)

SHA256：flight `ce8e61d32e3322ff197685f0b8c743fb966cad6776817b91407265cc419d5bef`；制动评估 `328a4110a5dde6e5bbbffc966d4cbe97877a8b57545cfa85babc4b064db180e1`；debug-truth评估 `e190753b22a264e13c7f5f3f0faf6bdcef40739ee4e918be`；ground map `eb2f461a722be100423c3dcdd3c3230acf0ee746a85b76f22d1732102806826e`；airborne map `60823cc6d71d35d8b4fb3f05fa689f95dd51b453fd35b6a3887e547df287822d`；launch manifest `ced8e9c11591c70ff814a728f37d9150e904ae8cac8e64026a721413ae71c287`。

## 下一子项 #269

在不改变 EGO 曲线 5 cm 管道、速度上限或 N05 准入的前提下，保留原全速度 `<0.03 m/s` 稳定 1 s 门，并增加起飞后垂向速度 `<0.01 m/s` 稳定 1 s 的发目标前置条件。这个门只控制是否发第一条目标，不替代曲线验收；使用新冷启动确认是否能达到，若不能则在发目标前安全结束并继续诊断。
