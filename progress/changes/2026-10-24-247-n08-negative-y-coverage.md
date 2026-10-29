# #247 N08 负 Y 观察覆盖尝试

关联对话摘要：[2026-10-24-247](../../collaboration/dialogues/2026-10-24-247-n08-negative-y-coverage.md)。

## 修改

- 新增 `n08_overhead_free_sector_view_decoupled_slow_vertical_return_negative_side` 支架 profile：保留 #246 成功 profile 全阶段，仅在原有正侧观察与下降前增加 yaw −π/2 观察／停留／回中。
- 同步更新 N05 runner allowlist、profile choice 和针对性单测。未改规划器、目标、速度上限、空间门或 VINS 健康阈值。

## 验证

- `python3 -m unittest tools.test_preflight_scan`：34 项通过。
- `bash -n tools/run_n05_preflight_layout.sh`、`python3 -m json.tool config/components/simulation/preflight_scan.json`、`python3 tools/project_status.py`、`git diff --check`：通过。
- N05 冷启动 #247 完成新增负 Y 观察和回中，但在首次 z=1.0→0.5 m 下降时 `normalized_cost_exceeded`，因此没有 post-release N05 gate、compute-only 或曲线证书。
- health 锁存不是 stale：快照源龄约 64/68 ms，`stale_observation=null`；PX4 HRT／ROS 时钟在锁存后仍有效。
- helper 清理 fixture、fresh readback 确认 DISARMED/landed、bridge disabled，控制话题无样本；项目容器停止 exit 0。

## 限制与后续

此 run 没有 same-identity post-scan map，负 Y unknown 是否减少未判定。无 XY 或制动数据，N08 未通过。#248 只延长首次下降时间 8→20 s，检验新增观察与下降动作的代价交互；若仍锁存，先审阅对应 health 快照，不重复本实验。
