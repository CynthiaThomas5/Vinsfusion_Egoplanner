# 修改与验证记录

- 日期／任务：2026-10-22／081。
- 对话摘要：[用户要求与执行决定](../../collaboration/dialogues/2026-10-22-081-agent-task-workflow.md)。
- 修改文件：`AGENTS.md`、`docs/remaining-small-goals.md`、`progress/CURRENT.md`，新增本记录与对话摘要。
- 行为变化：后续收到推进指令自动按 GOAL／CURRENT／milestones 选择或恢复一个有界任务；规定范围、预算、停止、复用已有成果、安全收尾和证据写回；答疑／文档请求不执行实验，默认完成一项就报告交接。该约定是仓库指导，不是外部调度器或程序硬超时。
- 任务拆分：N01 细化为 N01.1 证据缺口、N01.2 记录／评估工具、N01.3 补采与整体评估，允许继续细分以适配预算；CURRENT 指向尚未开始的 N01.1。N01 和各里程碑状态不变。
- 授权边界：默认不自动创建持续 /goal，不改 GOAL 契约、验收门限、可选研究依赖或实机范围；仅将用户要求的工作方式落地。
- 验证类型与结果：文档／结构／差异静态检查。`python3 tools/project_status.py` 退出 0，Structure/design PASS（80 个可选历史大产物链接缺失）；`git diff --check` 退出 0。修改前哈希对照确认既有文件只改 AGENTS、执行书、CURRENT；去掉新规则块后 AGENTS 与原文一致，原实施边界未改。GOAL、milestones、运行源码和参数均未改变；下一父目标 N01 仍为 not_started。五个本轮文件的空白／末尾换行检查通过。
- 保护：修改前文件哈希与原文快照在本机 `/tmp/d435i-agent-rules-081-baseline.json`；核对本轮只改上述三个既有文档，其余已有文件保留。
- 未验证：未编译、未运行算法测试／回放／SITL／实机，无运行资格或阶段升级。
- 下一步：用户说“继续下一项”时执行 N01.1，完成清单后交接。
