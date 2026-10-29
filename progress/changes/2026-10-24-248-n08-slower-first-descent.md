# #248 N08 负 Y 视角后的首段下降诊断

关联对话摘要：[2026-10-24-248](../../collaboration/dialogues/2026-10-24-248-n08-slower-first-descent.md)。

## 修改

- 新增 `n08_overhead_free_sector_negative_side_slow_descent` profile；仅将 #247 profile 首段 z=1.0→0.5 m 时长从 8 s 改为 20 s。
- 同步 N05 shell allowlist、Python choices 和 profile 单测。
- 未调整 planner、目标、空间／速度／health 门或 PX4 时间参考。

## 验证

- `python3 -m unittest tools.test_preflight_scan`：35 项通过。
- `bash -n tools/run_n05_preflight_layout.sh` 与 `python3 -m json.tool config/components/simulation/preflight_scan.json`：通过。
- SITL 完成负 Y view/return 后仍在首段下降 health-lock，cost=1.037158；源龄新鲜，PX4 时间域有效。无 post-release gate、compute-only 或 XY。
- fixture safe cleanup、fresh DISARMED/landed readback、bridge disabled、零控制样本；`tools/project.sh stop` exit 0。

## 结论与后续

延长下降时长没有解除拒绝，不重复调整该变量。#233 已有 negative-only profile 的 N05 成功证据，适合用来获取当前地图并避免 combined positive+negative 侧视；#249 将检查该 profile 在当前 start-hold query 下的同 run 结果。
