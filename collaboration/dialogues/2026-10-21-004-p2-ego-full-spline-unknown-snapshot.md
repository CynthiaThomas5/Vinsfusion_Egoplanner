# 任务对话摘要

- 日期与任务 ID：2026-10-21 / GOAL C full-spline guard 首次拒绝点同 epoch 快照诊断 #329。
- 用户目标与明确约束：继续完成 GOAL.md；维持单 D435i 仿真范围、第三方源码只读、规划器诊断无控制发布和真值输入；证据必须明确说明适用范围。
- 已确认的决定：复用 #328 已构建的 canonical-source full-active guard binary，只扩展 run-local probe，使其在首个最终样条拒绝 rosout 后立即请求一个 epoch/map_id 绑定的只读 occupancy snapshot。所有未知样点仍 fail-closed；不为增加 B-spline 而放宽安全门。
- 已确认的结果：attempt 01 因定位/建图 `telemetry_stale` 在目标前置门失败，排除。attempt 02目标成功发送但45秒无样条；392条拒绝全为in-map unknown。首拒绝点约55 ms后的同epoch/map_id快照中，对应0.1 m体素仍为unknown、inflation mask为0；3³邻域24/27为unknown。known map coverage为0.2357%。EGO有32条odom/depth lost警告，不能把零输出只归因于unknown guard。
- 待办：加长目标派发前的仿真运动／地图构建窗口复测起点体素可见性；不改unknown策略或把planner-only结果记作安全验收。
- 对应改动记录：`progress/changes/2026-10-21-004-p2-ego-full-spline-unknown-snapshot.md`。

仅保存必要脱敏摘要，不保存完整聊天。
