# GOAL C A* blocked endpoint fail-closed 候选（#312）

- 用户要求继续完成 GOAL.md；本轮聚焦 GOAL C unknown-space 规划安全，不放宽 unknown 策略。
- 仓库约束：第三方源码保持只读；实验补丁留在 `dependencies/patches/ego`，不进入 `dependencies/sources.json` 或 `src/vendor`；planner-only 运行不得订阅真值或发布控制。
- 决定：在隔离 patch 0020/0022/0023/0024 后加入 0025；A* 起点或终点格心若被阻塞就立即返回失败，不平移端点穿过 unknown/occupied cells。用真实 `GridMap`/`AStar` 类离线测 known-free、unknown、known-inflated 与 blocked goal。
- 结果：五包 Release overlay 构建通过；离线测试4/4通过；#312 planner-only run生成1条未执行 B-spline，记录103,635次 endpoint reject、0次池越界。日志133.7 MB，拒绝密度与回调重试率仍未知；使用run-local 0.5 m inflation。
- 未决：需降低日志频率并与不改A*逻辑的配对构建测调用率；需同刻地图快照、第二布局和净空检查。该证据不代表GOAL C/D/F或A–H通过。
- 证据：[报告](../../progress/evidence/p2-ego-astar-fail-closed-20261020-312.json)，[构建/测试记录](../../artifacts/runs/p2-ego-astar-fail-closed-20261020-312/build-report-0025.json)。
