# 2026-10-26 #311：新增 rear observation slow-descent N05 profile

- 基于 #307 的 17 阶段 rear-facing short-hold profile，唯一修改 yaw 回中后首个下降段时长：8 s → 12 s。目的是缓解 #307 在 z≈0.899 m、normalized cost=1.00986 的健康门拒绝。
- 将 profile 接入 scan probe 和 host wrapper；新增逐阶段回归，确认仅 index 14 的 duration 改变。
- `tools.test_preflight_scan` 42/42 通过；profile JSON、wrapper shell 语法、`project_status.py`、`git diff --check` 通过。未降低任何阈值。
- 静态报告：[证据](../evidence/n08-rear-short-hold-slow-descent-profile-20261026-311.md)、[JSON](../evidence/n08-rear-short-hold-slow-descent-profile-20261026-311.json)；对话摘要：[对话](../../collaboration/dialogues/2026-10-26-311-n08-rear-observation-slow-descent.md)。
- 尚无 SITL 证据。下一步使用全新冷启动 `n08-cancel-highspeed-prescan-20261026-311`，只在同身份 post-release N05 与 mission-current-area gate 通过后检查 N08 实时前向几何。
