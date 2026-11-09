# GitHub 源码发布与更新

目标远程为 `git@github.com:CynthiaThomas5/Vinsfusion_Egoplanner.git`，本地名为 `origin`。
本地仓库根目录是 `/home/work/D435i-groundstation/project`，不是外层部署目录。
该路径当前是指向 `releases/gs02-20261106-freeze01/project` 的符号链接；Git 配置和提交存放在实际源码目录内。

## 发布内容

本次发布将现有工作树作为项目快照整理，包括自维护 ROS 包、配置、仿真资产、依赖补丁、工具、使用文档和轻量验证记录。保留原有 Git 历史，不覆盖或回滚本地已存在的实现。
已有代码修改按当前状态保存，不将本次文档整理视作这些代码的新验收。

不上传以下本地内容：

- `src/vendor/`、`external/` 下的第三方展开源码（保留 README），按 `dependencies/sources.json` 获取。
- 构建、安装、运行会话、原始录包、大型日志、模型输出及 core 崩溃转储。
- 私钥、密码、Token、认证配置和原始私人对话。
- `小型无人机-IX35PRO/` 本地 CAD 参考资料；不删除本地文件，不将其当作运行依赖。
- 外层 `backups/`、`downloads/`、`releases/`、`runtime/` 等部署内容；它们不在本仓库根目录内。

`collaboration/dialogues/` 中的项目摘要和 `progress/` 轻量证据继续保留，原始私人聊天目录始终忽略。
许可证沿用现有包和第三方声明，见 `dependencies/README.md`。

## 首次上传与后续更新

```bash
cd /home/work/D435i-groundstation/project
git remote -v
git status --short --branch
python3 tools/project_status.py
git diff --check
# 先读取远程，确认现有分支，避免覆盖他人历史。
git ls-remote --heads origin
```

首次发布提交准备在本地 `main` 分支，正常推送：

```bash
git push -u origin main
```

如果远程已有不兼容的 `main`，普通推送会拒绝；先 `git fetch origin` 审查并合并历史，不使用强制推送。
历史仿真标签和运行环境分支不由该命令自动上传；README 中的环境获取仍引用 `docker/environment.json` 指定的原仓库。

后续修改先检查差异、按文件暂存、提交后再推送。需要完整复现时，另外传递经过哈希验证的运行镜像和必要实验数据；源码克隆不包含这些本地资源。

## 当前连接限制（2026-11-09）

当前执行环境中，默认 SSH 首先报 `/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf` 权限错误；使用不加载该配置的独立只读连接测试后，仍无法解析 `github.com`。因此本地远程 URL 配置不等于已经认证或上传成功，远程仓库内容和访问权限尚未确认。
应在具备正常网络及 GitHub SSH 权限的终端执行上述检查与推送命令；无需修改项目源代码。
