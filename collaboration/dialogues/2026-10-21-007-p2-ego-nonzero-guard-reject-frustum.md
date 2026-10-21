# 任务对话摘要

- 日期与任务 ID：2026-10-21 / GOAL C EGO 非零时刻 guard 拒绝点与深度视场配对 #332。
- 用户目标与约束：继续完成 GOAL.md，保持单 D435i 视觉导航范围；第三方源码只读；unknown 不得无条件作为 free；真值只允许隔离评估。
- 已确认结果：复用 #328 binary，在新 domain/partition 做75秒 planner-only run。目标派发但无 B-spline；425次拒绝中371次在t=0、54次在非零时刻；EGO有30条 odom/depth lost警告。捕获首个非零拒绝 `t=1.08 s` 的同 epoch/map_id快照：voxel `[123,120,6]` unknown、inflation=0，邻域18 unknown/9 free，known coverage约0.638%。snapshot请求第一次因 `no_fresh_fused_depth` 被拒，第二次成功。
- 视场核对：按深度源stamp插值 VINS IMU pose 并使用 D435i SDF 外参复算，相机光学坐标为 `[0.203,-0.381,0.217] m`；深度值超过0.2m近裁剪，但像素在图像上方，整个 voxel 超出当前竖直视场。该点 unknown 与未观测空间相符，不是障碍证明，也不能标为 free。
- 决定：不改 planner 或 unknown policy；下一步评估安全的视角／姿态观测，再只对 newly observed known-free space 规划。GOAL C remains pending。
- 对应改动记录：`progress/changes/2026-10-21-007-p2-ego-nonzero-guard-reject-frustum.md`。

仅保存必要脱敏摘要，不保存完整聊天。
