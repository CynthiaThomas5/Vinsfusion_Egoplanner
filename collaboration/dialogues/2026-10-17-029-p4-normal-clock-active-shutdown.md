# 2026-10-17-029：P4 正常时钟活动目标关闭

## 任务摘要

继续完成 `GOAL.md` 的 A–H 与 P0–P6，当前推进 P4 正常时钟活动目标 SIGINT 关闭路径。

## 用户约束

- 以证据推进，不以单次诊断冒充阶段通过。
- 旧实验来源只读；不调整时钟、freshness guard 或 EGO timeout 来掩盖问题。
- 本次没有运行控制器、PX4 或发布控制设定点。

## 决定

- #59 的 stale goal rejection 与 #60 的 freshness gate timeout 均保留为失败诊断。
- #61 在 pipeline warm-up 后增加逐项 freshness 计数；canonical `/clock` 下活动目标 SIGINT 通过。#62 用新 domain/partition 独立复测再次通过，得到 action 与 traj_server 匹配 ABORT、无后续 READY 和导航进程退出码0。
- 记录 #61 配对输入 freshness 间歇，以及 #61/#62 的导航回调空档与 EGO 输入/solver 错误；不将两次路径通过升级为输入稳定性或 P4 通过。

## 待决

- pose/depth 配对输入间歇及导航 callback gaps 的来源是什么；两次关闭路径通过后，输入与回调时序仍不稳定。
- 输入稳定后再执行轨迹跟踪、到达和更大范围 P4 验收。
