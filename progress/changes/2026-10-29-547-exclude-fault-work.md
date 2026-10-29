# #547 排除故障专项工作

用户明确“不用处理故障情况”，将范围从原#434仅跳过N10校准扩大为当前交付不要求故障专项校准、额外故障实现或N15正式六类注入/退出验收。N15不标passed：保持not_started并以scope_excluded/required_for_current_scope字段明确排除。N16/N17移除N15前置，原依赖备存；E故障部分及最终checklist明确排除，连续十分钟和正常任务核心证据仍要求。历史失败/不足不改、原条款保留追溯，最终报告必须披露未验收故障范围。

改动：GOAL、remaining-small-goals、CURRENT、milestones、goal-checklist及对话摘要。无运行源码、参数或冻结配置变化，不删除既有PX4/EGO/epoch处理。无实验/飞行，不启动N16。

验证：python3 tools/project_status.py、git diff --check；核对N15非passed、排除字段、N16/N17依赖和next_goal=N16一致。停止原因：本轮范围设置完成。唯一下一步N16.1正常完整负载协议准备。对话collaboration/dialogues/2026-10-29-547-exclude-fault-work.md。
