# 项目协作约定

## 每次开始

读取 README.md、GOAL.md、progress/CURRENT.md、progress/milestones.json，再按任务读取相关 docs 与配置。先运行 `git status --short --branch`；已有修改属于用户，不回滚或混入本轮任务。

本仓库根目录是 colcon 工作区，已有自维护和固定第三方可构建包。不要用空 package.xml、假 launch 或写死成功输出伪造实现；结构检查不能代替构建和SITL。

## 实施边界

- 当前只推进 P0–P6 单 D435i 仿真导航。语义、信念、探索仅预留接口。
- 修改前检查模块输入、输出、坐标与唯一控制发布者。第三方算法只保留一份，避免同名 ROS 包冲突。
- 旧 PX4-ROS2-SLAM-Control-Deploy 和 ROS_SEARCH 实验区是只读来源。迁入新项目必须记录原路径、版本、diff、哈希、许可及验证状态；不修改来源来适配新项目。
- 自维护源码在 src/own；第三方源码在 src/vendor。第三方修复另存 dependencies/patches，注明基准提交和应用顺序。
- 参数在 config，模型在 simulation。launch 只引用这些源文件；不维护多份相机外参、PX4 参数或地图配置。
- 任何在线真值输入只允许出现在 debug_truth；最终验收组合不得订阅真值位姿或完整世界地图。评估节点只读，禁止发布控制。
- VINS 重启、epoch 改变、时间倒退都取消目标和轨迹并重置地图。禁止隐式拼接会话。
- 所有 PX4 控制设定点与 OffboardControlMode 由 uav_px4_bridge 独占；模式由其状态机协调。定位适配不得发布控制指令。

## 对话和进度分开保存

- collaboration/dialogues/YYYY-MM-DD-NNN-topic.md：只保存本项目任务摘要、用户约束、决定和待决问题。不能作为测试通过证据。
- progress/CURRENT.md：当前状态唯一入口，保持简洁。只写已确认、证据推断、待确认、PROVISIONAL、下一步。
- progress/changes/YYYY-MM-DD-NNN-topic.md：每次有实质修改时写文件、行为变化、验证命令／结果、局限与下一步，并链接对应对话摘要。
- progress/milestones.json：阶段状态；通过必须引用证据。
- progress/evidence/：轻量验收报告。大日志、录包、地图放 artifacts/runs/<run_id>，报告引用其相对位置与哈希。
- 不自动保存完整私人聊天；原文导出如由用户提供，脱敏后放 collaboration/dialogues/raw，默认不入 Git。禁止凭据、Cookie、Token 和私人聊天混入提交。

## 完成前

检查与本次改动匹配的命令，结构任务运行 `python3 tools/project_status.py`。代码变更运行相应构建／测试，分别记录静态、回放、SITL、实机证据；不能互相替代。

更新 CURRENT、改动记录和必要里程碑。检查 `git diff --check`、拟提交文件与 `git status --short --branch`。未经明确要求不推送。结构检查通过只表示骨架一致。
