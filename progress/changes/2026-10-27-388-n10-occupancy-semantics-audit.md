# #388 N10 occupancy 语义审计

对话摘要：[2026-10-27-388](../../collaboration/dialogues/2026-10-27-388-n10-occupancy-semantics-audit.md)。

## 变更

- 新增只读报告，复核 #385 方箱内部 raw sphere 查询的位置、半径与源代码判据。
- 结论：查询球位于箱体内部，未覆盖 x 负向前表面；raw query 不含 inflation。EGO 官方碰撞使用 inflated 层。
- 修正 #387 报告到其归档 JSON 的相对链接，供结构检查解析。
- 没有运行飞行或改变运行逻辑；N10.3 仍未通过，N10 父状态保持 `in_progress`。

## 验证

- 直接检查 `grid_map.cpp`、`sphere_query.h`、`grid_map.h`、`ego_replan_fsm.cpp` 中 query、raycast、inflation 和 native collision callback 实现。
- 离线复用 #385 `n10-obstacle-alignment-forensics.json`：内部查询球与可见前表面间隔约 0.272 m；+0.5/+1.25 sim s 的同 identity raw 计数均为 free=160、unknown=0、occupied=0。
- 将源文件 SHA256、关键语义和证据局限写入 [#388 报告](../evidence/n10-raw-versus-inflated-occupancy-audit-20261027-388.md) 与机器报告。

## 局限与下一步

归档没有箱体迎机表面 occupied 点坐标或同刻 inflated point-query。内部 raw-free 不证明前表面或地图碰撞层失效，也不证明其有效。下一项 #389 准备只读表面/内部 raw 与 inflated 观测并保留 source/fusion stamp 与 identity；若需重现，只做观察，不加拒飞门。
