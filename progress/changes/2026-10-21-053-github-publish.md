# Git配置与GitHub首次工程提交

对应[任务摘要](../../collaboration/dialogues/2026-10-21-053-github-publish.md)。

- 远程为`git@github.com:CynthiaThomas5/D435i-VINS-EGO-ROS2.git`；本仓库使用既有Cynthia Thomas提交身份、现有GitHub密钥和SSH443，不改变全局Git传输配置，不生成或写入凭据。
- 原远程main为`e10ee7964795f887ae53d5db414aa17e27957dc9`，仅初始化README。以该提交作为父提交，保留历史，不使用force push。README保留项目名称和原始简介，并提供实际工程说明。
- 初始索引和状态备份在`artifacts/maintenance/git-publish-20261021-053/`；按用户本轮明确授权，将当前整理后的工作树整体提交。构建、第三方下载、日志、固定镜像、local实际配置和raw聊天继续忽略。
- 提交前检查源文件范围、文件大小和常见凭据格式；运行`python3 tools/project_status.py`、`git diff --check`并检查拟提交文件。未修改算法、模型或运行参数，沿用#052构建／133项测试／SITL证据，不另行宣称新飞行验证。
- 推送结果以本地main与`git ls-remote origin refs/heads/main`哈希一致为准；远程临时不可达时不得记录为成功。

局限：Git仓库不包含约1.4GB的固定镜像交付包，接收方仍需按docker/README.md取得固定镜像；跨机器冷安装及正式导航稳定性验收未完成。

暂存范围检查：946个文件、约7.6MB；没有构建／运行大文件、符号链接、实际local配置或常见密钥格式。完整`git diff --cached --check`发现原补丁内容中的上游空白及两份历史文档EOF空行；未改写锁定补丁，以免破坏补丁哈希与重放。此次修改的文档`git diff --check`通过，结构检查通过；原始空白检查日志保存在本轮maintenance目录。
