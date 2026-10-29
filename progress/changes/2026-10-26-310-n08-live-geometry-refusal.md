# 2026-10-26 #310：N08 前向几何实时拒绝

- 新 cold start 复现 N05 side-view 扫描；15/15 完成，#309 的返程段 1.094 cost 锁存未复现。支架释放后 same-identity N05 online/offline 通过，mission-current-area 通过，40 秒只读 preflight 通过。
- 新实时 full-body geometry gate 在目标/enable 前拒绝：仅起点保持和前 2.5 cm 查询触及 x=−1.05 m 后方 rotor-1 区域的 27 个 unknown cell；+0.05 m 到 0.6 m 目标、terminal hold 均没有 unknown；occupied=0。
- 复算的名义 rotor clearance 0.37479 m，小于既有空间+tracking余量 0.39868 m；保持现有失败关闭判据，不改预算或未知占据阈值。
- 独立安全读回 DISARMED/landed/at-rest、bridge DISABLED/control0；没有 goal/enable/takeoff。只停止当前项目容器，Exit(0)。
- 下一步在未解锁 N05 支架扫描中验证后向薄层视野；唯一 profile 变量是将 #307 yaw 回中后的下降时间 8 s 改为 12 s。目标 flight 仍只向前，不追加返航。
- 报告：[实时拒绝](../evidence/n08-forward-geometry-refusal-20261026-310.md)、[机器摘要](../evidence/n08-forward-geometry-refusal-20261026-310.json)、[unknown voxels](../evidence/n08-forward-unknown-slab-20261026-310.json)、[几何 replay](../evidence/n08-forward-reachable-geometry-replay-20261026-310.json)。对话摘要：[对话](../../collaboration/dialogues/2026-10-26-310-n08-live-geometry-refusal.md)。
