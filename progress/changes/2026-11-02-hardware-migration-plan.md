# 实机迁移规划与只读调查

- 本轮ID：HW-PLAN-20261102。目标：基于仓库与真实设备，交付可执行的Nano/D435i/PX4迁移方案。
- 对话：[摘要](../../collaboration/dialogues/2026-11-02-hardware-migration-plan.md)。
- 实际改动：新增实机执行方案及只读调查报告；历史路线增加当前入口；CURRENT记录规划完成与下一项H0.1；milestones的hardware_followup仅更新规划入口/范围，不改变任何仿真父目标状态或next_goal。
- 核心选择：优先保留现有Foxy驱动，独立工作区移植固定代码；必要改动涵盖ARM/ROS兼容、真实rig、非零偏置估计、深度单位、完整机体变换、真实时间、DDS版本与未武装分层启动。
- 验证：SSH只读环境与历史清单读取成功，范围/局限见[调查证据](../evidence/hardware-inventory-20261102.md)。`python3 tools/project_status.py`：Structure/design PASS，提示251个历史可选大产物缺失；该检查不代表构建/SITL/实机通过。`git diff --check`通过。本轮仅文档/状态元数据，无代码构建或运行验证需求。
- 未解：当前源码ARM/Foxy构建、真实采样与动态误差、满载、PX4固件/DDS/融合、外参与机体尺寸；所有实机阶段保持未通过。
- 停止原因：本轮规划任务完成。未执行安装/参数写入/飞行，未创建运行会话。
- 下一步：H0.1独立ARM/Foxy构建与真实传感器入口；H1前补固件/安装与拆桨条件，H2前补现场接管/场地。
