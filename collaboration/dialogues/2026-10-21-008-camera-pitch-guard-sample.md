# 改变视角后重新观测 guard 样本

用户要求继续完成项目 `GOAL.md`。本轮聚焦 GOAL C：复核 #332 的非零时刻 EGO 拒绝样点是否因超出 D435i 视场而保持 unknown，并检验安全视角变化后的在线深度是否能在同一地图身份中更新该区域。

约束与决定：只推进单 D435i 仿真导航；保留 unknown fail-closed；不改 vendor、PX4 控制链或生产配置；使用只读 MapStatus/快照观察，不发送导航目标；不订阅真值；run-local SDF 可添加视觉纹理但不得注入占据或真值。不得将单点诊断标为 GOAL C 通过。

结果：#333 的无纹理大角度尝试导致 VINS `stereo_features_insufficient` 和 map_id reset，因此排除跨 reset 比较；#334 因 observer 的 `KeyError` 没有后快照。#335 的较浅代表点和 #336 的原始 #332 光线向量在同 epoch/map_id 配对快照中均由 unknown 变为 known-free。#336 的相机在刹车后继续转动约 13°，因此增加 #337 时长匹配的加减速并将后快照提前到仿真时刻 34 s。#337 以原始光线向量复测：目标投影从 `(635,-351)` 到 `(490,51)`，对应 voxel `[122,118,5]` 从 unknown 变为 free；快照深度源龄109/113 ms，定位和 map ready，独立 NPZ 复算全部通过。

未决：这只是一个纹理增强 debug 场景中的单射线证据。真实机体姿态变化的安全规划、其他 unknown 区域覆盖、机体扫掠净空、轨迹执行、PX4 SITL 和实机验证仍待完成；GOAL C 与最终 A–H 保持 pending。
