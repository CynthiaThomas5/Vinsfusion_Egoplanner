# N08.2m #223：水平视角经中立回归失败诊断

日期：2026-10-24。父任务 N08 保持 `in_progress`。本次不是 N08 通过证据。

## 假设与唯一变量

假设 #222 的 cost 越线与 −π/2→+π/2 连续 180°扫动有关。本轮只把两个水平视角之间的路径改成左视角→yaw=0 回中／停留→右视角；顶板、box/column、其它支架阶段、停留时间、N05/EGO 门限和 unknown 规则不变。

## 结果

- Run：`n08-20261024-223-horizontal-views-via-neutral-01`；profile 有 23 阶段、526 仿真秒。
- 初始 N05 online/offline 同样拒绝 `ground_plane_insufficient_raw_occupied_voxels`，identity 为同一新 epoch/map；该 refusal 是观察前基线，不是 post-release 结果。
- 左侧 yaw=−π/2 观察和回中阶段完成。回中停留末尾最后有效定位 trace 的 normalized cost 为 0.97904；随后刚开始向 +π/2 转动即因 `normalized_cost_exceeded` 中止，最终读回 1.00292，超过固定上限 1.0。未调整健康门限。
- 这说明“只因直接做 180°连续转动”不足以解释越线；两侧视角的累计旋转／视觉条件仍可能有关，但因果未确定。raw VINS solver 记录持续到清理阶段；失败归类为 normalized-cost health refusal，而非已观察到的 `telemetry_stale`。
- 未到 N05 after/post-release gate；没有扫描后 map、body／hold／line raw query、compute-only、READY、XY 或制动数据。

## 安全收尾

`fixture-result.json` 记录 PX4 `ARMING_STATE_DISARMED`（枚举值 1）、fresh landed receipt（约 0.33 s）、支架 detached 且模型不存在，无 ROS 控制／goal publisher。仿真经 `bash tools/project.sh stop n08-20261024-223-horizontal-views-via-neutral-01` 停止，容器 exit 0。

## 后续

暂停继续增加 yaw 观察阶段。改用 #221 已通过 N05 post-release 的同场景 raw map，离线筛选一条位于 D435i 水平视场内、且 production body／terminal-hold／continuous-line 查询全 free 的短候选。候选仍须在新的 same-run N05 map 上重新计算，不能拿旧 map 替代 fresh gate。

原始运行目录：`artifacts/runs/n08-20261024-223-horizontal-views-via-neutral-01/`。

| 文件 | SHA-256 |
| --- | --- |
| `n05-run-inputs.json` | `503f0c7617ef25667e496d14a8c411632533b4572874b189174db0442625f078` |
| `fixture-result.json` | `e2110215b84a06f0367b45f6daef4d10ce132701a9c425c899b1c99138ed406a` |
| `fixture-trace.jsonl` | `ceedb78bf9f83b8618331033d420980db28f9965e834730d5b82f86caddd4a42` |
| `fixture-vins.jsonl` | `4ed5b5e3a5d4e9c9a87da3d533acfef53cd662175df98efdadaab525ca9bd67e` |
| `n05-before/n05-live-entry-check.json` | `10f5c3a6ad9210ab042c2ca18deb3da735f26c4d3c637f26a4173e297bf02045` |
| `n05-before/n05-offline-entry-replay.json` | `1e927386d32402ac2276fc29b7b07f14e19a9bf8691ffb227658c7e4c79714c5` |
