# N06.3 起点与保持区观测覆盖诊断

日期：2026-10-23。Goal 完成模式，用户指定范围 N06。父目标 N06 和 S4 保持 `in_progress`；本报告只完成入口 unknown 的几何视场诊断，不代表 N06 正向出口通过。

## raw unknown 视场复算

新增只读工具 [analyze_n06_observation_coverage.py](../../tools/analyze_n06_observation_coverage.py) 对 wall-r10 与 corridor-r10 的 snapshot-03 复算生产闭格球查询，再将 unknown cell center 投影到精确 `last_fused_depth_source_stamp_ns` 相机位姿和内参。每份记录都复投影了该 source stamp 之前的全部采集相机位姿。完整坐标、时戳、map identity、文件哈希和分类数见[机器可读报告](n06-observation-coverage-diagnostics-20261023-095.json)及[原始分析结果](../../artifacts/runs/n06-observation-coverage-20261023-r01/report.json)。

| 布局 | 查询体积 | raw unknown / free / occupied | unknown 中心：相机后方 | 小于 0.2 m 近裁剪 | 水平画面外 | 垂直画面外 | 当前／全采集序列成像内 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wall-r10 | N05 body 球，r=0.730618 m | 1,801 / 410 / 0 | 1,093 | 379 | 180 | 149 | 0 / 0 |
| wall-r10 | terminal hold，r=0.980618 m | 4,048 / 804 / 0 | 2,419 | 640 | 591 | 398 | 0 / 0 |
| corridor-r10 | N05 body 球，r=0.730618 m | 1,807 / 384 / 0 | 1,153 | 368 | 157 | 129 | 0 / 0 |
| corridor-r10 | terminal hold，r=0.980618 m | 4,085 / 836 / 0 | 2,546 | 642 | 529 | 368 | 0 / 0 |

各分类按“后方、近裁剪、水平出画、垂直出画、成像内”的互斥顺序计数，且每行总数等于 raw unknown。体素闭格与原查询数完全一致。wall/corridor 分别检查了 692/697 个 source 时刻及之前的采集相机位姿；这些 pose 下，四种球的 unknown cell center 均没有落入几何成像区。

该证据支持入口体积缺少单目 D435i 直接观测覆盖这一解释，尤其是相机后方与近距体素。它只投影体素中心，没有验证采样深度值、射线穿越、遮挡、每个体素内部点或分类更新，因此不能排除射线／分类缺口，也不能作为已知 free 证明。未把 unknown 改为 free，N05 半径和验收门槛均未改变。

## live readiness 分类

- wall-r10 的 map identity 稳定，source/fusion age 为 0.106/0.018 s，MapStatus 为 fresh；一次 body query 却返回 `no_fresh_fused_depth`，EGO 没有曲线。N03 曾记录 pending depth pair 时服务保守拒绝、但最近完成融合仍 fresh 的情况；r10 未记录该请求时的 pending 标志，所以它是合理候选解释，尚未证实。
- corridor-r10 在 10 秒 probe 窗口内没有收到 fresh odometry，故未发送 goal。输入录制包含 356 条 optimized odometry，但 localization 自 sim 39.597 s 起为 `normalized_cost_exceeded`，并持续至录制结束；probe 缺少后续有效 odometry 与 health lock 相符。

## N06.4 单变量观测协议

r20 在隔离 textured surround 内保持平移不动并执行完整 360° yaw，但首次 `n_pts size: 0` 出现在 sim 13.432 s；首个 `normalized_cost_exceeded` 是 sim 13.630 s，当时 truth yaw 约 2.30°／2.58°。旋转健康迅速锁定，没有 map snapshot。

r21 保持同一 surround、同一固定位置、同一 360° 端点，仅把 yaw 角加速度降为原来的 1/16，使峰值角速度从约 0.209 降至 0.052 rad/s、相位时长从 30 s 增至 120 s。假设是角速率主导了 r20 的早期健康锁定；判据是 localization 是否健康到完整转向结束。采集器时长设为 308 wall 秒，覆盖 profile 最长 300 秒运行时限及 8 秒余量，避免慢扫描末段缺失。

运行命令：

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r21 wall_box_column 84 motion_n06 config/components/simulation/n06_yaw_360_very_slow.json
```

若 health lock，保留 motion/input 落盘并在等待快照前停止 runner；若完整通过，继续 fresh identity 快照和无控制 live EGO 诊断。PX4、bridge、controller、setpoint 与飞行任务均关闭。

## 验证与限制

- `PYTHONPYCACHEPREFIX=/tmp/n06-python-cache python3 -m py_compile tools/analyze_n06_observation_coverage.py`：通过。
- `python3 tools/analyze_n06_observation_coverage.py --output artifacts/runs/n06-observation-coverage-20261023-r01/report.json`：通过；raw 查询数与 #093 r04 完全一致，两布局 body/hold 的采集序列几何成像数均为 0。
- 后续 #097 执行 `bash -n` 并通过 `bash tools/project.sh test`（243 tests 与 navigation adapter integration）。
- r21 尚未运行；N06 的两布局实际 live EGO 全机曲线、terminal/emergency hold 与 replanning handoff 仍未通过。

下一步：在同一 Goal 范围内运行 r21，分析唯一主要变量为 yaw 角速率的结果；N06 保持未通过。
