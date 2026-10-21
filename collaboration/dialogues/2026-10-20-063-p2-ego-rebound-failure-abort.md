# GOAL C EGO 碰撞回弹 fail-closed 与重试率 #314

## 任务与约束

- 继续推进 GOAL.md 的完整 P0–P6/A–H 目标；本次只作独立 EGO planner 诊断，不宣布阶段或目标通过。
- 按 AGENTS.md 保留既有工作区修改，不暂存、不回滚；第三方源码改动只放隔离 patch，不修改 src/vendor 或 dependencies/sources.json。
- 运行不启动 PX4、控制器或 trajectory server，不执行样条，不订阅真值，也不发布控制。

## 决定

- 基于 #313 的计数候选建立 0027 实验 patch：无碰撞前自由控制点时设 STOP_FOR_ERROR；A* 路径失败时也直接失败，不再伪造起点或移除失败段继续。
- 保留 collision policy 为 fail-closed；run-local inflation 0.5 m 与 unknown-as-obstacle 仍是诊断配置，不提升为默认值。

## 已确认

- 固定 Jazzy Release 环境 5 包构建成功，实际 GridMap/AStar 离线用例 4/4。
- #314 live 观察到 20,421 次 no-free-pre-collision-point abort、2,054 次 A* 失败 abort，零 A* 池越界，未再出现旧的“drone is in obstacle”逐次错误。
- 运行仍有 22,940 次失败规划尝试与 9 次成功尝试；探针收到 1 条独立 B-spline。它未执行，不能作为可用避障证据。
- 源码审计发现 EGO FSM 的 10 ms wall timer 在 SEQUENTIAL_START 里每次调用 10 个 global plan trial，失败后保留同一状态；运行失败次数与约 1000次/s 的重试规模相符。现有 1.0 s replan threshold 没限制 initial-plan failure retry。
- 起点附近约 (-0.0061,-0.0035,-0.0017) 的 A* 点被记录为 in-map、unknown、raw occupancy 0、inflated 1；表明缺少碰撞前已知自由控制点。无同刻占据快照和净空测量，来源仍待查。
- GOAL C/D/F 与 A–H 均 pending。

## 下一步

- 在 0028 实验 patch 中，用现有 1.0 s replan interval 对 initial global-plan 失败做冷却，仍保留活动目标并继续等在线地图更新；对新目标重置冷却。
- 再跑同场景，确认规划失败数明显下降，并确认地图变为可用后仍能产出轨迹。
- 捕获 accepted spline 同时刻地图快照并计算机体包络净空；只有这一步通过后，才安排后续执行测试。
