# 任务对话摘要

- 日期与任务 ID：2026-10-21 / GOAL C 延迟目标派发与 full-spline unknown 起点诊断 #330。
- 用户目标与明确约束：继续完成 GOAL.md；维持单 D435i 仿真导航范围、第三方只读、控制单一发布者边界、真值仅debug用途；不得把未知区域推定为free。
- 已确认的决定：复用#328 planner binary和#329 run-local快照observer，仅把目标前连续ready等待延长至25秒并扩大观察窗；保留现有unknown fail-closed guard、场景和障碍参数。
- 已确认的结果：目标前已有4次传感器motion阶段变化，目标状态ready；75秒内无B-spline。425次碰撞守卫拒绝均为in-map unknown/raw-free/not-inflated，367次首拒绝在t=0，其他样点最远到t=1.59秒。首拒绝后48 ms返回的同epoch/map快照显示对应voxel仍unknown、inflation=0，3×3×3邻域13 free、14 unknown、无occupied；known coverage 0.617%，本轮无odom/depth lost警告。
- 待办：检查mapping free-ray 投影、D435i视场、机体位姿与unknown邻域的坐标关系；不放宽unknown门，也不将planner-only结果当作避障通过。
- 对应改动记录：`progress/changes/2026-10-21-005-p2-ego-full-spline-delayed-goal.md`。

仅保存必要脱敏摘要，不保存完整聊天。
