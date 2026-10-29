# 2026-10-26 #311：rear scan 健康门拒绝

- rear-facing slow-descent profile 的新 cold start 在 stage 7/17 回程刚开始时触发 normalized cost=1.048986 > 1.0；锁存发生在 x≈−0.985 m，视觉 residual 组占主导。
- 计划改变的 stage 14 descent 12 s 未执行；不能据此评价 slow-descent 假设。
- fixture detach/删除、PX4 disarmed/landed/at-rest、bridge disabled/control0 均有独立读回；容器 Exit(0)。没有 N05 post-release、N08 mission 或飞行。
- 对照 #309/#310 后，单变量下一步是把该 profile stage 7 的 1.2 m return 从 60 s 延长到 100 s；其余 profile/阈值保持固定。
- 静态 profile：[报告](../evidence/n08-rear-short-hold-slow-descent-profile-20261026-311.md)；运行拒绝：[报告](../evidence/n08-rear-scan-health-refusal-20261026-311.md)、[JSON](../evidence/n08-rear-scan-health-refusal-20261026-311.json)。
