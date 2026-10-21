# 项目骨架初始化

- 任务 ID：2026-10-16-001。
- 对话：[架构初始化摘要](../../collaboration/dialogues/2026-10-16-001-project-bootstrap.md)。
- 改动：创建 README、AGENTS、架构／接口／目录／迁移／验收文档；模块目录占位；依赖和来源清单；三个设计 profile；进度与对话模板；只读结构检查工具。
- 目的：建立独立项目边界，让后续 Agent 可区分设计、实现和运行证据。
- 验证类型：本地结构与配置一致性，非 ROS 编译或 SITL。
- 验证命令：`python3 tools/project_status.py`；最终结果见 [骨架验收报告](../evidence/bootstrap-check.json)。
- 未验证：全部导航运行链路；源码尚未导入，P0–P6 均未通过。
- 下一步：固定依赖与现有修复的源码基准，开始 P0。
