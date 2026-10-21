# GOAL C A* 调用率对照 #313

基于 #312 的 fail-closed 候选建立 0026 隔离诊断 patch。它给 A* 两个调用点增加计数并按 10,000 次输出摘要，抽样详细拒绝日志，移除逐次的 A* 调用点错误日志；没有改变寻路和优化决策。patch 未进入 canonical EGO 源码或 dependencies/sources.json。

固定 Jazzy 容器中的 5 个 EGO 包构建成功，真实 GridMap/AStar 离线策略测试 4/4 通过。planner-only 对照运行以 #312 attempt 02 为控制，场景障碍几何、wall phase、规划器配置、目标和力命令一致，传感器采样与仿真时序并非确定性重放。#313 汇总 209,658 次 A* 调用，205,139 次位于 check_collision_and_rebound；其中端点拒绝 137,241 次、搜索失败 40,452 次、搜索成功 27,446 次。initControlPoints 有 4,519 次。目标仍收到 3 条未执行 B-spline。EGO 日志从控制轮 132,000,635 bytes 降到 35,450,589 bytes，但仍有 112,265 条“drone is in obstacle”错误，故日志节流没有解决规划失败循环。

验证：bash artifacts/runs/p2-ego-astar-callsite-rate-20261020-313/build-and-test-container.sh（5 包构建，离线 4/4）；bash artifacts/runs/p2-ego-astar-callsite-rate-20261020-313/run-container.sh（planner-only，无 truth/control/PX4）；补丁对 0025 重建树 git apply --check 与逐文件回读比较通过。

证据：[运行报告](../evidence/p2-ego-astar-callsite-rate-20261020-313.json)，[构建报告](../../artifacts/runs/p2-ego-astar-callsite-rate-20261020-313/build-report-0026.json)，[源码清单](../../artifacts/runs/p2-ego-astar-callsite-rate-20261020-313/source-manifest-experiment-0026.json)，[A* 诊断 patch](../../dependencies/retired-code-20261021.json)。

局限：未调用快照服务；无同刻占据体素或净空评估；三条样条未执行；run-local inflation 为 0.5 m；实验结果不能证明 canonical EGO 或避障安全。

下一步：#314 隔离 patch 0027 在无法找到碰撞前自由控制点或 A* 失败时设置 STOP_FOR_ERROR，由 planner-only live run 检查 B-spline 是否被正确阻止；再追查当前位置体素的占据/unknown 来源。
