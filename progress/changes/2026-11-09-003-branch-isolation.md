# BRANCH-ISOLATION-001：保留演示基线，建立探索分支

对话摘要：[用户目的](../../collaboration/dialogues/2026-11-09-003-branch-isolation.md)。

改动：固定标签 demo-baseline-2026-11-09 指向 61a707f；外层 backups 保存已验证完整 Git bundle；新增 explore 分支及独立工作树。稳定 project/main 源文件和启动入口保持原样。探索分支新增工作流及 AGENTS 约束、README 导航和 CURRENT 记录；外层本地 AGENTS 引导后续开发进入 explore。

验证：`git bundle verify` 通过；`python3 tools/project_status.py`、`git diff --check` 通过；核对 main 仍为原提交且工作区干净，探索分支与基线标签推送后核对远程引用。新工作树首次结构检查因未展开 vendor 而出现 9 处历史源码链接缺失；随后独立复制本机现有 src/vendor 后检查 PASS，未修改检查器。副本不入 Git，未共享稳定 build/install，也未复制 external 和原始运行数据。历史本地大型证据按可选缺失处理。

局限：本轮没有重跑演示、ROS 构建、SITL 或硬件实验，不生成新资格；Git bundle 不含忽略的构建、镜像或数据。共享设备、容器名、状态与安装尚未隔离，不并行运行或用探索环境覆盖演示环境。milestones 和硬件下一项不变。

停止原因：完成源码分支和目录隔离。后续从 explore 目录开展有界探索，部署前按实际影响建立独立环境与恢复资料，验证并获准后再晋级 main。
