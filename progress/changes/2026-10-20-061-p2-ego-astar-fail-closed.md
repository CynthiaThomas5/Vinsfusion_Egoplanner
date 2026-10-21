# GOAL C A* blocked endpoint fail-closed 候选（#312）

- 对话摘要：[ #061](../../collaboration/dialogues/2026-10-20-061-p2-ego-astar-fail-closed.md)。验收证据：[runtime/behavior report](../evidence/p2-ego-astar-fail-closed-20261020-312.json)，[build/test report](../../artifacts/runs/p2-ego-astar-fail-closed-20261020-312/build-report-0025.json)。
- 文件与行为：新增隔离 patch `dependencies/patches/ego/0025-astar-blocked-endpoint-fail-closed-experiment.patch`，仅在临时重建源树生效。unknown cell由实验patch 0020判阻塞；A*选中的起点或终点格心只要占据查询为阻塞就立即返回失败，不再沿阻塞方向移动端点。未改动 `src/vendor/ego_planner`、canonical patch 列表、配置默认值或唯一控制发布者。
- 验证：patch 0025 binary dry-run/apply 后候选文件与手工修改副本逐字节相同；固定 Jazzy 容器构建 `traj_utils`、`plan_env`、`path_searching`、`bspline_opt`、`ego_planner` 共5包通过；真实 `GridMap`/`AStar` 离线测试4/4通过（known-free path成功；unknown start、known inflated start、blocked goal fail-closed）。planner-only #312 在 ready epoch派发目标并收到1条 B-spline；103,635次 endpoint reject（unknown 86,310、known inflated 17,325），0次局部池越界。未启动 PX4/控制器/traj_server，无真值或控制 topic，未调用快照服务。
- 局限：隔离策略与 run-local 0.5 m inflation；EGO日志133,664,589 bytes，拒绝调用密度约4.4k/s，可能影响时序，调用重试根因未知。没有同刻体素快照、第二场景、净空评估或执行轨迹；单条 B-spline不代表目标到达或避障通过。GOAL C/D/F 与 A–H 状态不变。
- 下一步：对失败诊断限频，以canonical逻辑保持不变的对照构建估算A*调用频率；之后用fresh同刻地图快照核对unknown/inflation与路径净空，再决定是否提出canonical行为变更。
