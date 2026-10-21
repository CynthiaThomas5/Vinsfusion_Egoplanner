# GOAL C 未知起点与 A* 局部池边界审计（#308）

- 对话摘要：[ #059](../../collaboration/dialogues/2026-10-20-059-goal-c-unknown-start-cell-audit.md)。轻量证据：[unknown start-cell audit](../evidence/p2-ego-unknown-start-cell-audit-20261020-308.json)。
- 本次改动：新增只读审计报告和两次失败前置采集记录；新增的 run-local harness 仅用于隔离诊断。未修改 `src/vendor/ego_planner`、`dependencies/sources.json`、canonical patches、默认参数、PX4控制或旧来源。
- 确认：A*池为100³、0.1 m步长，节点搜索边界1..98；`ConvertToIndexAndAdjustStartEndPoints` 会将被判阻塞的起点沿远离终点方向逐步移动。#306新鲜快照中，原点和#307碰撞点均为unknown且膨胀mask为0；patch 0020将unknown判为阻塞。此解释得到支持，但缺少#307的同刻地图和每次A*输入坐标，仍属因果推断。
- 验证：#308 attempt 01/02 均未通过快照fused-depth新鲜门，未提交目标；报告保留拒绝原因与日志哈希。后续#309静止输入MapStatus停在`map_reset_acknowledged`；#310出现Gazebo Ogre渲染器SIGSEGV，均未发goal或产生快照。相关来源、快照和planner日志哈希写入证据报告。
- 结果：#307已确认的A*路径vector越界读有#0023隔离保护；未知起点问题未修复，未生成或执行轨迹。无PX4、控制器或在线真值输入。GOAL C/D/F和A–H继续pending。
- 局限与下一步：#306快照是同场景profile的跨run证据；#308失败尝试没有地图数据。为`AstarSearch`及坐标转换增加隔离、低频输入／越界诊断，记录起终点、中点、量化索引、查询格心、体素分类、调整次数和越界坐标；在复现后再判断地图策略。
