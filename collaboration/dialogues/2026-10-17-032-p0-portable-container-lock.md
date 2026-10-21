# P0 固定容器归档、整仓重建与状态检查器

- 用户目标：继续完成本项目 `GOAL.md` 的 A–H 与 P0–P6 全部验收；本次按当前最早缺口推进 P0，不把 P4 局部任务当作整体目标。
- 约束：保留进入本轮前的 staged/unstaged 状态；不清理已有容器或镜像、不提交或推送；大型镜像放在 `artifacts/runs` 并留哈希，不宣称编译等于运行或飞行通过。
- 发现：原 Jazzy/Harmonic 基础镜像无项目内配方；OS 包仅有部分锁定。`tools/project_status.py` 还把所有运行 profile 永久限制为 `design_only`，与 Goal 要求检查器随实现演进相冲突。
- 决定：导出基础与 VINS 派生镜像为 SHA-256 固定归档并保存 Debian 包清单；在派生镜像的全新目录重建当前所有 `src` 包。状态检查器允许 `design_only`、`in_progress`、`runtime_ready` 并检查 `runtime_ready` 一致性，继续强制最终视觉组合禁用真值位置、GPS 和 debug PX4 定位。
- 实施结果：17/17 包构建成功；P0 状态更新为 passed，GOAL A–H 仍为 pending。镜像归档被 Git 忽略，需要与源码单独传递。
- 待确认：空 Docker daemon 导入、完整 package tests/launch、传感器运行、SITL 飞行、PX4 EKF2 融合均未由本轮验证。
- 对应记录：`progress/changes/2026-10-17-032-p0-portable-container-lock.md`；验收报告为 `progress/evidence/p0-portable-container-rebuild.json`。
