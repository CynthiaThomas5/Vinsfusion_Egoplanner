#271 N08 正确 profile 起飞状态空窗诊断

- 新 cold start 显式使用低速 planner profile；launch manifest 与磁盘配置路径／哈希一致。
- N05 15/15 支架扫描完成，post-release 与 mission current-area 在线／离线准入通过；40.00149 s preflight 通过。mission 前 raw-map capsule 与 home-pad 检查通过。保留扫描器泛化定位警告。
- Offboard enable 后 bridge 到 TAKEOFF、PX4 解锁并检测起飞，随后在 ACTIVE 前由 runner fail-closed。`/localization/status` 存在 0.344954 s 回执空窗，超过既有 0.2 s 新鲜度门；两端样本均 valid TRACKING。原因仍未唯一确认。PX4 执行降落并 disarm。
- 无 EGO goal，沉稳门未运行，无新增制动数据。未调门限。归档安全状态与证据见 [`n08-preactive-localization-gap-20261025-271.md`](../evidence/n08-preactive-localization-gap-20261025-271.md) 与对话摘要 [`#271`](../../collaboration/dialogues/2026-10-25-271-n08-takeoff-status-gap.md)。
- 下一子项 #272：在有效 raw-map 证书后、enable 前关闭未使用的 `/grid_map/occupancy` PointCloud2 observer，验证是否减少状态回调间隔；本假设待 SITL 验证。
