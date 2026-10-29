# N08 #310：live forward geometry 拒绝

- 用户授权：按规划继续完成 N08；单目标到点停止，不自动返航；需要返航时另发 180° 转向和前向 EGO 命令。
- #310 N05 支架扫描完成 15/15；同身份 post-release/current-area N05 online/offline 和 read-only preflight 都通过。#309 返程段 health lockout 没有复现。
- N08 live geometry gate 在目标／enable 前拒绝：后方 x=−1.05 m 的 27 个 raw unknown cell 与初始 rotor-1 扩张查询相交，导致 hold 和首 2.5 cm 查询失败；前进 5 cm 后查询至目标、terminal hold free，occupied=0。当前门限的空间+tracking 余量 0.39868 m，大于这些 unknown voxels 到 rotor 碰撞体最近距离约 0.37479 m，故保留拒绝。
- 无 N08 goal、return goal、control enable、takeoff 或制动数据。独立状态 DISARMED/landed、bridge DISABLED/control0，容器 Exit(0)。
- 下一步仅对未解锁 fixture 做 rear-facing observation；把 #307 回中后的下降时长 8 s 改为 12 s，其余 profile 与阈值不变。飞行仍是单程前向。
- 证据：`progress/evidence/n08-forward-geometry-refusal-20261026-310.md` 和同目录 JSON/replay/raw-cell 清单。
