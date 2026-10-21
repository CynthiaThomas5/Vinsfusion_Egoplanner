# P2 EGO pose history=100 filter 交付诊断

日期：2026-10-17

- 用户目标：继续推进 GOAL.md 中的 P0–P6，不降低验收范围。
- 用户约束：保护已有 staged／unstaged 工作；只修改自维护源码或记录第三方补丁；本轮限定于 P2 单 D435i 仿真诊断，不启动 PX4 控制或实机。
- 已确认：patch 0015 在有效 #37 运行观察到 EGO pose filter 计数冻结。为排除 #33 中重复诊断订阅负载，本轮在 patch 0015 分支仅将现有 pose reader history 从25改为100。
- 决定：patch 0016 保留为可选诊断补丁。#40健康60秒窗口仍出现29条 in-window timeout，history=100未消除停顿；不将其作为生产修复或里程碑通过证据。#38 world 路径失败、#39 telemetry_stale 运行排除。零 `message_lost` 不足以判定 reader resource rejection 或 executor delay。
- 实施范围：新增补丁、隔离构建与 runtime 证据，更新 P2/P0 证据索引和当前状态。无外发消息、推送或提交。
- 对应改动记录：[progress/changes/2026-10-17-013-p2-ego-history100-filter-delivery-diagnostic.md](../../progress/changes/2026-10-17-013-p2-ego-history100-filter-delivery-diagnostic.md)。
