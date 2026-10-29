# #338 N10.3 运行入口未采样

状态：**未进入校准样本；不计作规划器结果。** ROS/PX4 只读预检及 official_ego 起飞准入均通过，之后 mission wrapper 在 flight runner 启动前退出。没有 goal、解锁或飞行。

`validated-ego-goal-graph.txt` 仅含 `Unknown topic '/navigation/ego_goal'`，而 `n09_runtime.sh` 直接运行一次 `ros2 topic info` 后才启动 recorder/flight runner。按脚本执行顺序推断，这是 ROS graph 首次发现延迟导致的退出；当时没有捕获明确错误文本。稍后只读重查同一 topic 时已发现唯一 `uav_navigation` publisher 与唯一 `drone_0_ego_planner_node` subscriber，说明 topic 本身存在，首次查询时序未就绪。

最终读回 bridge `DISABLED`、`landed=true`、`armed=false`，PX4 `arming_state=1`；随后停止了本项目容器。不会把这次写成飞行失败或通过。

已在 `tools/n09_runtime.sh` 将该入口改成最多 20 次、每次间隔 0.5 秒的 topic graph 等待，并要求 supervisor publisher 与 EGO subscriber 各 1 个。下一次按同一 horizon=2 预声明协议重新启动，完整输入哈希另记。文件与读回哈希见本报告 [JSON](n10-calibration-startup-20261026-338.json)。
