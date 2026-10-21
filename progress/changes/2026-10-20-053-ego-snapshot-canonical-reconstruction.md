# EGO 快照服务补丁纳入可重建依赖链

日期：2026-10-20

相关对话：[EGO 快照服务依赖重建](../../collaboration/dialogues/2026-10-20-053-ego-snapshot-canonical-reconstruction.md)

## 改动

- 将 EGO patch 0021 加入 `dependencies/sources.json` 的 canonical patch 序列，排在 0019 后；实验 patch 0020 仍排除。记录15份补丁的 SHA-256 与应用工作目录／剥离层数。
- 新增 `tools/fetch_ego.py`，从固定上游提交校验 commit 与许可证 SHA-256，应用 canonical 补丁，只物化五个 planner 包和许可证；已有 target 一律拒绝覆盖。新增离线测试覆盖四种补丁路径上下文、哈希拒绝、包子集和不覆盖行为。
- 修订 EGO patch 记录、接口／建图说明和构建说明，区分 canonical 重建能力与未修改的 `src/vendor/ego_planner` 副本。

## 验证

- `python3 tools/test_fetch_ego.py`：通过。
- `python3 -m py_compile tools/fetch_ego.py tools/test_fetch_ego.py`：通过。
- 对上游固定提交 `23a8d5a191711dd65633df689bd00f55d4dea8f9` 实际运行取源工具：15个补丁应用成功，生成五个规划包；许可证哈希通过，与 #297 完整构建源码的52个源文件（含 LICENSE）逐字节一致。来源清单见 `artifacts/runs/p2-ego-snapshot-canonical-build-20261020-297/ego-source-manifest.json`。
- 无旧工作区 overlay 的新 build/install 目录里，colcon 发现并构建16/16个项目 ROS 包；退出码0。`GetOccupancySnapshot.srv` 在该 install 中成功 introspect。完整命令、镜像、源码／二进制哈希与日志见 `progress/evidence/p0-ego-snapshot-canonical-build-20261020-297.json`。
- 构建脚本首轮在 `source /opt/ros/jazzy/setup.bash` 前启用 `nounset`，未启动编译；修复初始化顺序后干净全包构建通过。首次取源原型也因未记录上游 `src/planner` 与项目扁平 `planner` 根路径差异而在 patch 0004 失败；现按每个补丁记录的工作目录和 strip 值应用，并通过实际上游重建复核。

## 局限与下一步

- 原 `src/vendor/ego_planner` 副本未改动；直接从该副本构建不会包含 patch 0021。干净 checkout 可用 `tools/fetch_ego.py` 重建，已有副本由工具拒绝覆盖。
- #292–#296 的地图运行仍是隔离候选安装；#297 没有新增地图运行。已知体素比例低于配置地图的1%，一格墙面中心变化及首帧 SDF 离群点原因未解。
- GOAL C 的完整性、ghosting、unknown 安全、延迟和净空，及规划、PX4、控制与最终无真值验收仍未完成；GOAL A–H 和 P0–P6 状态不因此标记完成。
- 下一步在匹配捕获阶段定义可见表面 ROI，比较栅格侧选与深度／定位误差，并分析大墙边缘点；之后再冻结地图覆盖与 ghosting 指标，继续 D/E/P4–P6。
