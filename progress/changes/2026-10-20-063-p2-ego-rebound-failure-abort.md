# GOAL C EGO 碰撞回弹 fail-closed 与重试率 #314

基于 #313 的 EGO 候选建立隔离 patch 0027。在 check_collision_and_rebound 找不到碰撞前自由控制点时，记录样本体素状态、设 STOP_FOR_ERROR 并返回；A* 搜索失败也设 STOP_FOR_ERROR 并返回，不再把 in_id 强置为0或删除失败 segment 后继续。planner_manager 会把所有 optimizer alternative 失败传回 false，不生成轨迹；但任一 alternative 成功时仍允许发布结果。

固定 Jazzy Release 容器中的5个 EGO 包构建成功，已有 GridMap/AStar 离线测试4/4。planner-only run #314 的 MapStatus ready，有925个 occupied 点和409次深度转发。运行记录20,421次无自由前置点 abort、2,054次 A* abort、零 A* pool exit；旧的逐次“drone is in obstacle”消息变为0。目标仍收到一条 B-spline；内部记录9次规划成功、22,940次失败尝试。样条没有执行，不能计为避障通过。

根因进一步指向 FSM 重试节奏：exec wall timer 是10 ms，SEQUENTIAL_START 每次调 planFromGlobalTraj(10)，失败后继续停留在 SEQUENTIAL_START。这个 100 Hz × 10 trials 的结构与约994次/s的运行失败计划量相符。运行的 1.0 s fsm/thresh_replan_time 参数没有约束 initial-plan 失败重试。起点附近 A* 查询点被记作 in-map、unknown、raw free、inflated blocked；目前无同刻完整体素快照，不能判断相机近场、free-ray 清除或 footprint 配置哪一项导致该状态。

验证：bash artifacts/runs/p2-ego-astar-rebound-abort-20261020-314/build-and-test-container.sh（五包构建、离线 4/4）；bash artifacts/runs/p2-ego-astar-rebound-abort-20261020-314/run-container.sh（planner-only，无真值/控制/PX4）；0027 对 #313 候选树 git apply --check 和逐文件回读比较通过。

证据：[运行报告](../evidence/p2-ego-rebound-failure-abort-20261020-314.json)，[构建报告](../../artifacts/runs/p2-ego-astar-rebound-abort-20261020-314/build-report-0027.json)，[源码清单](../../artifacts/runs/p2-ego-astar-rebound-abort-20261020-314/source-manifest-experiment-0027.json)，[隔离 patch](../../dependencies/retired-code-20261021.json)。

局限：0027仍是实验 patch，未改 canonical；0.5 m inflation 未冻结；no-free-abort 日志仍很多；一次 B-spline 未执行；没有同刻栅格回读、净空、碰撞、SITL 或 PX4 证据。

下一步：为 initial global-plan 失败试验冷却间隔，使 FSM 持续等待地图更新而不每10 ms重试十组候选；对新目标复位冷却。重跑后收集同刻 map snapshot，先验 B-spline 净空，不执行未经验证的样条。
