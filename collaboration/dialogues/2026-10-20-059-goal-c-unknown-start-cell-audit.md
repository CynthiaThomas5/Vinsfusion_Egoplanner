# GOAL C 未知起点与 A* 局部池边界审计（#308）

- 用户目标继续为完成 `GOAL.md` 的 P0–P6 和 A–H；当前只推进单 D435i 仿真导航。
- 已审查 #306 四份新鲜同 epoch 快照：起点原点和 #307 碰撞点体素均为 raw unknown、inflation mask 为0；#307 隔离 patch 0020 会把 unknown 作为碰撞。结合源代码，A* 在起点被阻塞时沿远离目标方向以0.1 m重复挪动，直至找到非阻塞体素或越出约5 m的局部池。288次池边界拒绝与该路径一致，但无法把全部错误逐一归因。
- #308 两次尝试均未取得新鲜 fused-depth 快照（`no_fresh_fused_depth`/`depth_source_stale`），没有发目标；第二次运动指令记录也未产出。已有 #306 存档仅为同 profile 跨 run 证据，不冒充 #307 精确时间地图。
- 决定：patch 0020 与 0023继续隔离，不改变 canonical 参数／源码和里程碑。#309静态run停在map_reset_acknowledged，#310 Gazebo Ogre崩溃；下一步为每次A*调用记录原始start/end、中点、量化索引、查询格心、占据类别与精确越界点，再判断地图策略。
- 证据：[审计报告](../../progress/evidence/p2-ego-unknown-start-cell-audit-20261020-308.json)。GOAL C/D/F与总目标均 pending。
