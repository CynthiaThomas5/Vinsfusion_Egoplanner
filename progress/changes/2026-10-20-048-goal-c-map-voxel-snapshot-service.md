# GOAL C 在线体素快照服务候选 #292

对话摘要：[2026-10-20-048](../../collaboration/dialogues/2026-10-20-048-goal-c-map-voxel-snapshot-service.md)。

## 改动

- 新增 `uav_interfaces/srv/GetOccupancySnapshot.srv` 并加入接口构建清单。候选 EGO `plan_env` API `/mapping/get_occupancy_snapshot` 需要调用方给出精确 epoch/map_id；检查最近融合的有效深度、融合时间、待处理更新、地图内位姿及 timeout 状态后，返回带 frame/time/origin/尺寸/resolution/order 的 raw occupancy 和独立 inflation mask。map reset 会清除融合深度有效状态。
- 新增 `tools/capture_live_occupancy_snapshot.py`，先读 MapStatus，再按身份请求并复查身份；校验数据布局、分类值、计数、freshness 与配置哈希，归档 NPZ 并逐数组回读，同时请求错 epoch/map_id 以验证拒绝。
- 新增 EGO patch `0021-occupancy-snapshot-service.patch`，基于上游 `23a8d5a191711dd65633df689bd00f55d4dea8f9` 的 canonical 0019 之后状态，独立于 patch 0020。仅在干净隔离副本中应用和构建；`src/vendor/ego_planner` 及 `dependencies/sources.json` 未修改。
- 同步更新接口契约、mapping 说明、项目 README、patch 索引、CURRENT、里程碑和证据目录。P2 保持阶段表 `passed`，P6 保持 `in_progress`；GOAL C 未完成。

## 验证

- `bash artifacts/runs/p2-map-voxel-snapshot-service-20261020-292/build.sh`：Jazzy 干净隔离 install 中 6 个包构建通过；`ego_planner_node` SHA-256 `691471c8e6679bf9eb867f9724407cb4f23f09675367bd44353084e65fbe6530`，`libplan_env.so` SHA-256 `c2f3c5d409fa3138c400feb0884750b2c3b64c1183989ef981c3f772dc9617b0`。
- 在只读 `src/vendor/ego_planner` 中运行 `patch --dry-run -p1 < .../0021-occupancy-snapshot-service.patch`：两个目标文件检查通过，无应用／写入。
- `python3 -m py_compile tools/capture_live_occupancy_snapshot.py` 与三个运行／构建脚本的 `bash -n`：通过。
- Live attempt 01 在首个 fused depth 前返回 `no_fresh_fused_depth`，按预期 fail closed；attempt 02 仅有一个 forwarded depth，快照全 unknown，排除为地图内容证据。attempt 03 使用 ROS domain 141 与隔离 Gazebo partition，在 forwarded depth count 23→26 时捕获 240×240×60 栅格；unknown/free/raw occupied/inflated 分别为 3,448,918/5,846/1,236/6,297，已知体素占0.2049%。wrong epoch 与 wrong map_id 分别以 `epoch_mismatch` 与 `map_id_mismatch` 拒绝；NPZ 两数组精确回读。服务耗时45.03 ms，源龄132 ms；原始数组6,912,000 bytes，压缩归档10,033 bytes，SHA-256 `608e105d6bf15c6bd063b50a37bbd23e1195df2335c4fe1049732e80434d9118`。
- ROS graph 未发现真值、控制话题或 PX4／controller 节点。debug force-driven fixture truth recorder 独立记录，不进入 localization/mapping。
- `python3 tools/project_status.py`：PASS（结构一致性检查；明确不代表 ROS build 或 SITL 验收）。`git diff --check` 与 `git diff --cached --check`：PASS。
- 运行报告：[run-report.json](../../artifacts/runs/p2-map-voxel-snapshot-service-20261020-292/run-report.json)；轻量证据：[evidence JSON](../evidence/p2-map-voxel-snapshot-service-20261020-292.json)。

## 局限与下一步

本轮只验证候选 service/readback，不证明 coverage、free-space 准确性、墙面几何、地图重影、累计地图、净空、未知空间规划语义、planner 接受度或导航行为。已知体素约0.205%，且只成功采集一个正向快照；单线程 EGO executor 上一次6.912 MB原始数组响应约45 ms，并发客户端及更大地图未测。patch 0021 还没有纳入 canonical 依赖重建；接下来审查其来源锁定／重建流程，并做独立运动场景下的覆盖、几何、时延、重影与 unknown-space 评估。
