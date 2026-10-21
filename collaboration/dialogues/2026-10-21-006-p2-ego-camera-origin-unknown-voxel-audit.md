# 任务对话摘要

- 日期与任务 ID：2026-10-21 / GOAL C EGO 相机射线端点与起点 unknown voxel 源码核对 #331。
- 用户目标与约束：继续完成 GOAL.md；第三方源码保持只读，最终规划 unknown fail-closed，真值不得参与验收。
- 已确认结果：#330 在目标 stamp `22.012 s` 的 IMU/body pose、SDF 外参推算的深度相机中心和 planner 首拒绝点都落入 voxel `[120,122,1]`。同 epoch 快照显示该格 unknown、inflation=0。固定 EGO 的 raycaster 把相机格作为终点，在终点 step 返回 false；调用方只对成功 step 累加 miss/free，因此射线不清除相机自身 endpoint voxel。D435i housing collision box 中心也位于此 voxel，直接标记整格 free 需要明确定义 self-filter/footprint 语义。该机制强烈吻合 t=0 unknown 拒绝。
- 结论边界：这是源码、坐标与现存快照的对齐核对，没有干预运行；不解释 #330 的全部非零时间首阻点，也不证明 unknown 物理上 free。端点格和相机／机体自身几何重叠，不能直接把它作为普通 free voxel 写入地图。
- 决定：保持未知空间阻塞，不改第三方源码或 canonical manifest；下一步先明确 planner 对自机 footprint 与传感器近场盲区的几何契约，再验证隔离候选。
- 对应改动记录：`progress/changes/2026-10-21-006-p2-ego-camera-origin-unknown-voxel-audit.md`。

仅保存必要脱敏摘要，不保存完整聊天。
