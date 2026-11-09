# HW-DOC-20261102 实机模块执行任务书

- 目标：把迁移规划细化成可按模块直接交给Agent实施的任务书。
- 实际改动：新增docs/hardware-agent-workbook.md；原方案增加入口；CURRENT与milestones.hardware_followup登记任务书及下一HW01。前轮未提交文件保留，仅按本次要求补相关入口。
- 覆盖：HW01–HW14，包括环境、D435i、rig/session、VINS/localization、mapping、EGO/navigation、DDS、机体与时间、入口/负载、拆桨联调、悬停、短目标、避障和交付。包含依赖、实际源码入口、最小验证、完成条件、产物、阻塞处理与恢复提示词。
- 代码核对新增事实：桥接package.xml依赖ros_gz_bridge/uav_sim；实机应处理构建闭包与SDF运行耦合。现有n08 compute_only重映射不等于EV-only，任务书要求实际发布图检查。仅作任务定义，未实现。
- 对话：[任务摘要](../../collaboration/dialogues/2026-11-02-hardware-agent-workbook.md)。
- 验证：`python3 tools/project_status.py`结构PASS（251个可选历史大产物缺失提示保留）；`git diff --check`通过；一次文档检查确认HW01–HW14卡片有序齐全、本地链接有效、代码围栏配对。人工核对依赖无循环及拟建命令明确标注未实现。本轮只有文档和状态入口修改，不启动构建、SITL、SSH采集或飞行。
- 未解项：各HW模块尚未执行；真实固件、安装量测、满载和动态精度沿用前轮未确认状态。
- 停止原因：文档交付完成。没有新运行会话需要清理。
- 下一项：HW01，按任务卡在独立ARM/Foxy工作区实际构建；后续执行范围由用户指令与CURRENT记录确定。
