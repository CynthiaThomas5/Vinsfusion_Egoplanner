# #339 N10.3 horizon=2 PX4 校准协议

状态：**执行前协议固定。** #338 未进入采样：一次立即的 ROS graph 查询在 `/navigation/ego_goal` 尚未发现时返回 Unknown topic，wrapper 在 runner/observer 启动前退出。终态保持 disarmed/landed，无 goal 或飞行。

本次仍执行 #338 的同一单变量对照：只把 `planning_horizon_m` 从 5.0 m 改到 2.0 m，其他 planner/mission/health/map 参数不变。入口脚本 `tools/n09_runtime.sh` 现在对 `/navigation/ego_goal` 最多等待 10 秒，并精确确认一个 `uav_navigation` publisher 与一个 `drone_0_ego_planner_node` subscriber；未达标仍在解锁前拒绝。

原目标仍为 16 m 单程、+0.1 m 高度、+0.2 rad yaw、3 sim-s dwell；只有完整目标成功才开始 600 sim-s ACTIVE hold。固定 SE(3) 真值、raw VIO、实际速度、tracking、map age、接触和 PX4 落地读回条件均按 [#338 协议](n10-independent-calibration-protocol-20261026-338.md) 原样执行。

本轮的候选输入哈希和 startup fix 明细在[结构化协议](n10-independent-calibration-protocol-20261026-339.json)。
