# 2026-10-26 #297 N08 运行时配置 fingerprint 修正

- #297 新冷启动 N05 支架扫描 6/6、释放后 online/offline准入、40.01s只读preflight通过，但 mission 在发目标／enable 前将 goal JSON 错当成编译源码并拒绝。实际没有解锁或飞行。
- 失败后 4s 独立 readback：bridge DISABLED/control disabled，PX4 DISARMED/landed，control topics 0；project stop Exit(0)。
- `validate_trial_source_fingerprints` 现在对该运行时 profile 仍执行严格 hash 比较，但比较对象改为当前冷启动 runtime manifest；compiled-source 检查不变。
- 新增 runtime profile manifest 正／误哈希回归。验证：`bash tools/project.sh test`，362 tests 与 navigation-adapter integration PASS。
- 证据：[拒绝记录](../evidence/n08-runtime-profile-manifest-refusal-20261026-297.md)。对话：[摘要](../../collaboration/dialogues/2026-10-26-297-n08-runtime-profile-manifest.md)。
