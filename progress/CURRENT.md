# 当前状态

更新时间：2026-10-30。历史 `sim-nav-v1.0.0` 是已通过 N17 的 X500 版本。当前源码切换到约 250 级仿真近似机体，不能继承旧版的多场景、重复或长时资格，也不代表真实机体标定。

- 当前近似模型与官方地图参数的一次默认房间 16m 任务通过，见[模型适配报告](evidence/quad250-adaptation-20261030-592.md)；NavRL 多柱场景的 16m GUI/SITL 任务也通过，见[柱群报告](evidence/navrl-pillars-20261030-600.md)。两者均为单次日常任务，不计入新的正式 N11–N17 次数。
- 当前可复现配置含 `room`（默认）、`floorplan2` 和 `pillars` 场景；多柱演示命令为 `./start.sh fly pillars`。RViz 使用 Orbit 三维碰撞地图视角，保留已探索障碍历史层；#603 相机第一视角试验已撤回。
- 固定容器已单独保存在 `runtime-environment-v1` Git LFS 分支，SHA 和不可变 commit 见 [`docker/environment.json`](../docker/environment.json)。Linux amd64、NVIDIA/Docker/X11 设备要求及不支持范围见 [README](../README.md)。
- 当前工作项：将本工作树已有模型、场景、启动、测试和证据修改整理为可复现的 GitHub 快照；目标标签 `sim-nav-quad250-2026-10-30`。干净独立检出已完成全部依赖恢复、18包ROS构建、PX4完整构建、751单测和3套ROS集成；快照发布入口见README。

用户明确要求将现有工作树整体固化并上传。忽略的 `artifacts/` 运行日志/大文件、`.runtime/` 会话状态和机器本地凭据不作为源码发布；历史报告保留相对引用与哈希。
