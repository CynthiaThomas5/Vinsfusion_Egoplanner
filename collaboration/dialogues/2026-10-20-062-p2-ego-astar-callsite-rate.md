# GOAL C A* 调用率对照 #313

## 任务与约束

- 用户要求继续完成 GOAL.md 的完整 P0–P6/A–H 目标，不以单轮诊断或报告替代最终验收。
- 遵守 AGENTS.md：旧依赖只读，第三方改动仅以标注基准与顺序的隔离 patch 保存；不改 src/vendor 和 dependencies/sources.json；不启动 PX4、控制器或轨迹执行；没有真值订阅或控制发布。
- 保护仓库已有大量未提交修改，不暂存或回滚。

## 本轮决定

- 基于 #312 的 0025 候选，创建只用于统计／日志采样的 0026 patch，区分 initControlPoints 与 check_collision_and_rebound 两个 A* 调用点。
- 以 #312 attempt 02 为控制，使用相同场景几何、wall phase、规划器配置、目标与力驱动命令序列运行候选；仿真时间戳和传感器采样不做确定性回放。
- 候选仍由 planner-only 组合运行；规划输出只作诊断，任何 B-spline 均不执行。

## 已确认

- 五个 EGO 包在固定 Jazzy Release 容器构建通过；实际 GridMap/AStar 离线策略测试 4/4。
- #313 总计 209,658 次 A* 调用，205,139 次来自 check_collision_and_rebound；137,241 次该调用点端点拒绝、40,452 次搜索失败、27,446 次搜索成功。初始化调用点为 4,519 次。
- 仍有 112,265 条“drone is in obstacle”日志，目标仍收到三条未执行 B-spline。相对 #312-02 的 132.0 MB 日志，本轮 35.45 MB；这是诊断结果，不是性能或安全验收。
- 静态代码检查发现无碰撞前自由控制点时基线分支会退回 in_id=0；A* 失败时碰撞回弹分支会删掉失败段并继续。下一轮以独立 patch 测试这两类情况是否应强制 STOP_FOR_ERROR。
- GOAL C/D/F 与 A–H 仍未完成；地图同步快照、净空评估、轨迹执行、SITL/无真值视觉闭环均未通过。

## 待决

- #314 planner-only live run 是否在无法找到自由起点/无 A* 路径时拒绝发布 B-spline。
- 是否需单独修复深度映射中当前位置体素 unknown/inflated 的来源；本轮尚未取得同刻体素快照。
