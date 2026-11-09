# GS02任务规划

目标：写可执行冻结/迁移任务；不实际部署。

改动：新增docs/tasks/GS02-freeze-debian-migration.md；CURRENT登记计划；milestones登记GS02 not_started，不修改HW10验收状态；新增脱敏对话摘要[033](../../collaboration/dialogues/2026-11-05-033-gs02-migration-task.md)。

只读验证：SSH成功；目标/etc/os-release=Debian13.7、uname=x86_64、docker存在、约127GB可用；既有project目录和镜像119e6564…5880a存在。非交互密钥登录失败，随后使用用户提供密码完成本次认证，不存储凭据。远程command -v uav-groundstation/codex未返回路径，需在迁移阶段核实登录环境，不能据此断言未安装。

局限：未生成冻结包、未迁移、未执行GUI或新的飞行/感知实验；032实时性问题保留。停止原因：任务编写完成。下一项GS02.1。

完成检查：python3 tools/project_status.py 返回0，Structure/design PASS（251项可选历史产物缺失；不代表运行验收）；git diff --check返回0；已复核git status，既有修改保留，未提交或推送。
