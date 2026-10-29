# 2026-10-26 #313：后向观察移到低位回收之后

- 目标：针对 #307/#312 回中后下降定位代价越门，测试先完成低位回收、再上仰观察后方薄层的路线。
- 修改：新增 `n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view` profile；前 10 阶段沿用 #312，z=1→0.5→0 m 段前移到最终后向观察之前，后向 yaw=−π 与短保持改在 z=0/pitch=−0.35 rad，最后在地面高度回转到 0。profile 时长仍为 462 仿真秒。将 profile 加入 fixture runner、宿主 wrapper 和 profile 回归测试。
- 依据：#248/#307/#312 的下降锁存；D435i SDF 视场几何表明低位约 20°上仰后，已知 unknown slab 的投影角落在镜头视场内。视场估算不是 map coverage 证据。
- 静态验证：44 项 `tools.test_preflight_scan`、`tools/project_status.py`、JSON、shell 语法、diff check 均通过。
- 验收：待 #313 冷启动 SITL、释放后 N05、只读 preflight 和 N08 前向几何；门禁未通过前不发目标或启用控制。
- 证据：[profile 报告](../evidence/n08-low-rear-view-profile-20261026-313.md)、[机器摘要](../evidence/n08-low-rear-view-profile-20261026-313.json)、[对话摘要](../../collaboration/dialogues/2026-10-26-313-n08-low-rear-view-profile.md)。
