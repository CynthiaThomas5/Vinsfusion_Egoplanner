# REPO-PUBLISH-001：整理 GitHub 发布快照

对话摘要：[发布要求](../../collaboration/dialogues/2026-11-09-002-github-publishing.md)。

## 目标与实际改动

将现有源码仓库连接到 `CynthiaThomas5/Vinsfusion_Egoplanner`，完善 README，保存可发布的当前工作树快照。

- README 更新仓库地址、项目定位、仿真/Nano/地面站范围、部署前提、常用操作、文档索引及许可说明。
- `.gitignore` 增加 core 转储、本地凭据目录和本地 CAD 参考目录；不删除本地文件。
- 增加 `docs/github-publishing.md` 说明发布范围、普通推送和环境迁移限制。
- 本地 `origin` 配置为用户指定 SSH URL，保留原提交历史。当前已有代码及记录纳入用户要求的项目快照，不声称是本轮新实现或已重新验收。
- CURRENT 增加发布记录；milestones 和硬件下一项不变。

## 验证与限制

- `python3 tools/project_status.py`：PASS；历史本地大型产物缺失链接单独报告，不当作运行证据。
- `git diff --check` 与 `git diff --cached --check`：PASS，无空白错误。
- 3,718 个发布候选文件检查：无超过 5 MiB 的文件，未发现常见私钥、GitHub Token 或 AWS Access Key 特征；该静态检查不代表穷尽所有凭据格式。
- 本轮仅整理发布，不修改算法实现，不新做 ROS 构建、SITL 或硬件实验；既有代码验证状态继续以 CURRENT 和各证据为准。
- 默认 `git ls-remote` 被本机 SSH include 配置权限错误阻断；独立 SSH 配置检查仍报 `Could not resolve hostname github.com`。远程现有分支及认证尚未确认。`git push -u origin main` 因同一 SSH 配置权限错误失败；独立 SSH 配置下的实际推送也因 DNS 解析失败退出，未上传成功。

停止条件：完成本地整理和快照保存；网络不可用时将上传保持为待完成，提供正常网络终端的推送命令。不强制推送、不声称上传成功。

## 产物与下一步

产物：根 README、忽略规则、发布说明和当前源码快照提交。网络恢复后先检查远程分支，再执行 `git push -u origin main`；若被拒绝先审查远程历史。

## 权限恢复后的继续执行

- 网络已恢复，通过 HTTPS 读取目标仓库，远程 main 为 `2a6ab273983c2c3b6f7d458b00a89a7013008d95`，只含初始 README 标题。
- 已保留远程初始提交并合并进本地项目历史，解决 README add/add 冲突时保留本轮完整项目说明，不强制推送。
- GitHub SSH 返回 `Permission denied (publickey)`；启动官方 GitHub CLI 设备登录，等待用户完成账号认证后推送与验证。
