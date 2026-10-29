# 2026-10-26 #309：记录 N05 扫描健康拒绝

- 完成一次新 cold-start N05 支架扫描尝试；负 Y 侧视 profile 在第 7/15 阶段遇到 normalized cost 1.094002 > 1.0，未运行 N08 mission。
- 做了只读时序审计：锁存对应单个高视觉残差样本，后续 solver 代价回落但健康锁存保持；不修改任何健康门限。
- 独立 PX4/bridge readback 确认 DISARMED、landed、at-rest、DISABLED、control0；fixture 移除，项目容器安全停止且退出码 0。
- 下一步仅做一次同 profile 独立冷启动，检验该尖峰是否随初始化而变化；相同返程段再次健康锁存时停止该路线重复并基于对照设计新的有界 profile。
- 运行报告：[证据](../evidence/n08-prescan-localization-refusal-20261026-309.md)；机器摘要：[JSON](../evidence/n08-prescan-localization-refusal-20261026-309.json)；对话摘要：[对话](../../collaboration/dialogues/2026-10-26-309-n08-prescan-localization-refusal.md)。
