# 对话摘要：N08 #222 terminal-hold 水平观察

- 当前目标是完成完整 N08；用户指令与 N08 acceptance 不变，N07 #198/#200/#204 已通过项不重测。
- #221 证明 N05 gate 通过、真实顶板 raw occupied、body sphere start/goal free；EGO 半径 0.730618 m。0.980618 m terminal-hold spheres 仍有 41 / 16 unknown。候选 +Y0.6 line sweep 中间段通过，仅终端 hold 失败，因此没有启动 compute-only 或 XY。
- 新未知格在 start 的后方 y≈−1.05m，以及 target 前方 y=1.25–1.45m。#222 只增加 home hold 时 yaw −π/2/+π/2、pitch0 的水平视角，维持顶板和同一 wall_box_column、所有 safety threshold 与 raw unknown 规则。
- N05 same-run gates 与原半径 full query 全 free 才进入隔离 compute-only；真实横向执行还需要已知的保守 stopping boundary。

## #222 run result

- Run `n08-20261024-222-horizontal-views-01` reached stage 14/20, the continuous −π/2 to +π/2 yaw sweep, then failed closed with `normalized_cost_exceeded` at 1.00967; threshold stayed 1.0. The trace peaked at 0.99485 near yaw 1.004 rad immediately before health invalidation. Raw VINS solve records continue during cleanup, so the observed failure is cost-related; the 180° sweep is a causal hypothesis, not a proven root cause.
- Initial N05 online/offline both refused `ground_plane_insufficient_raw_occupied_voxels`; no after/post-release map or same-map body/hold/path query exists. No compute-only, READY, XY or braking run occurred.
- Final result confirms DISARMED and landed, fixture detached and removed, and project container stopped exit 0. Full evidence: [#222 report](../../progress/evidence/n08-horizontal-views-20261024-222.md).
- #223 keeps the same scene, views and thresholds but returns to neutral and pauses between the two 90° horizontal views. This tests whether reacquiring the central view prevents the cost rise. All unknown handling remains fail-closed.
