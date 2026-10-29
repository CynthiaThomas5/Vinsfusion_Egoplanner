# #508 取消地图表面误差数值门

关联[对话](../../collaboration/dialogues/2026-10-29-508-remove-map-surface-limit.md)。用户明确授权，将config/acceptance_n12.json升为revision11，只移除raw_map_surface_geometry.thresholds.surface_center_error_sample_max_m。新增tools/map_surface_policy.py，缺测/非有限值/缺覆盖仍INSUFFICIENT；兼容旧配置原数值FAIL。更新通用离线评估器和独立N12 wall/cylinder评估副本；新冻结发布artifacts/runs/n12-20261029-508-surface-policy/release。旧配置/评估器副本、所有原报告保持；在线候选和VINS8迭代未修改。

验证：51项策略/通用验收单测、13项障碍几何测试通过。归档重评保持原数值计算，只在验证所有snapshot SHA后复用未变的wall分类/表面数值，再重新执行完整通用验收和柱体证明。#506仍需地图分类通过，#504仍需队列覆盖；不随本授权取消。下一：完成归档重评并补足第三次独立正式合格运行，N12仍in_progress。

收尾补充：新增策略单测已去除对artifacts中历史配置副本的依赖，改用仓库冻结配置核对仅两项用户授权指标差异；51项测试再次通过，见policy-tests-portable.log。
