# #604 当前项目快照固化与发布

用户授权固化整个现有工作树并上传现有GitHub仓库。对话摘要：[记录](../../collaboration/dialogues/2026-10-30-604-github-snapshot-publication.md)。

- 已将#592–#603的模型、参数、场景、材质、工具、测试、许可及轻量证据纳入源码；README改为当前快照标签和固定环境commit恢复流程。
- 快照标签：`sim-nav-quad250-2026-10-30`；远端：`CynthiaThomas5/D435i-VINS-EGO-ROS2`，main。旧X500标签保留。
- 独立干净目录从源码commit `21082b32d89a7ebf7fe0b6469ca5003bcb887c6c` 恢复全部锁定依赖；18个ROS包构建通过；PX4完整1141步构建通过；751项单测和3套ROS集成通过。
- 首次临时worktree在容器内的绝对Git元数据路径不可见，ROS已通过、PX4尚未开始；将验证目录转换为独立克隆后PX4完整构建通过。这是验证目录形式问题，项目源码未调整。
- `python3 tools/project_status.py`、`git diff --check`通过；NavRL原始world保留原字节，gitattributes仅豁免其原有行尾空白。未发现凭据模式；忽略运行日志、缓存、机器本地配置。
- 日志：`artifacts/runs/snapshot-20261030-604/tests.log`、`px4-build.log`。本轮未新增飞行；当前模型16m GUI/SITL证据见#592/#600/#603。
- 固定环境LFS分支commit与镜像指针SHA/大小核对一致；本轮未重新下载1.48GB镜像对象或进行物理异机运行。已验证平台要求仍为Linux amd64/NVIDIA/Docker/X11；驱动和硬件变化须复测。
- 完成范围：当前源码快照和可复现部署入口；不转移旧X500正式资格。下一步：接收设备按README恢复并运行`./start.sh fly pillars`。
