# 任务对话摘要

- 日期与任务 ID：2026-10-21 / GOAL C canonical full-active-spline guard 诊断 #328。
- 用户目标与明确约束：继续完成 GOAL.md；只推进 P0–P6 单 D435i 仿真导航。第三方源码只读；规划器诊断不接控制或在线真值；不得把结构、构建或 planner-only 结果记作飞行安全通过。
- 已确认的决定：在 #297 pinned canonical reconstruction 上保留隔离实验，按0029、0030、0031、0028、0032顺序应用；0032仅移除最终样条守卫的 2/3 时间截断。补丁不进入canonical依赖清单，GOAL C和阈值继续pending。
- 已确认的结果：五包 Jazzy Release build通过。planner-only运行45秒发送目标但没有B-spline；439次guard拒绝中438次是t=0附近unknown，另1次在t=4.530秒检查到inflation mask。后者确认full-interval guard拦截了尾段候选；没有B-spline所以没有配对occupancy snapshot。EGO日志有57条`odom or depth lost`，不可把零样条单独归因于0032。
- 待办：run-local probe在首次 final-spline rejection时捕获同 epoch snapshot（即使没有B-spline），随后重复固定场景；不放宽门限或改写为通过。
- 对应改动记录：`progress/changes/2026-10-21-003-p2-ego-full-active-spline-guard.md`。

仅保存必要脱敏摘要，不保存完整聊天。
