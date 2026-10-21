# P0 固定容器归档、整仓重建与状态检查器

- 任务 ID／日期：032／2026-10-17
- 对话摘要：[P0 容器归档与状态检查器](../../collaboration/dialogues/2026-10-17-032-p0-portable-container-lock.md)
- 修改文件：`docker/Dockerfile.vins`、`docker/README.md`、`dependencies/sources.json`、`dependencies/README.md`、`config/README.md`、`tools/project_status.py`、`README.md`、`progress/CURRENT.md`、`progress/milestones.json`、`progress/goal-checklist.json`、`progress/evidence/README.md` 和 P0 证据报告。
- 行为变化及原因：导出 PX4/Gazebo Jazzy/Harmonic 基础镜像和 VINS 派生镜像为 `artifacts/runs/p0-container-image-bundle-20261017-01/px4-ros2-gz-and-d435i-vins-images.tar.zst`；包版本清单及 `SHA256SUMS` 便于离线核验。状态工具不再永久拒绝已实现的 runtime profile，同时保留最终组合无真值位置辅助约束。
- 验证类型：静态结构检查、归档完整性、Docker load、ROS 全仓静态构建。
- 命令与环境：`zstd -t`；在归档目录 `sha256sum -c SHA256SUMS`；`zstd -dc ... | docker load`；固定 `d435i-vins:dev` 镜像内以全新 build/install/log 目录运行 `colcon --base-paths src build`。ROS 2 Jazzy，17/17 包，退出码0。
- 结果及证据位置：[P0 固定环境与17包重建报告](../evidence/p0-portable-container-rebuild.json)。控制台、colcon events、installed setup、源文件 SHA 清单和工作树状态快照均在 `artifacts/runs/p0-container-image-build-20261017-01/`；镜像与 Debian 包清单在 `artifacts/runs/p0-container-image-bundle-20261017-01/`。
- 未验证与 PROVISIONAL：Docker load 在已有镜像缓存的 daemon 执行，未在空 daemon 单独导入；大归档不在 Git，须另行交付。没有运行 package tests、launch、传感器、PX4 控制、SITL 飞行或实机。结构检查不代替这些验收。
- 下一步：继续 P1 单 D435i 动态输入与时间／几何核验，基于 P1/P2 独立校准冻结 F 阈值；之后恢复 P4 live 导航修复验收，并逐步推进 P3/P5/P6 与 A–H。
