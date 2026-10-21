# GOAL C EGO 全局规划失败冷却 #315

用户继续推进 `GOAL.md`，本轮沿用 P0–P6 单 D435i 仿真导航边界；旧 PX4/ROS 实验区只读，第三方 EGO 变更只写入实验 patch，不能把结构或 planner-only 证据写成完整验收。

本轮在 #314 的隔离 EGO 树上新增 0028：全局规划失败后，`SEQUENTIAL_START` 与 `GEN_NEW_TRAJ` 按已有 `fsm/thresh_replan_time=1.0 s` 冷却重试，使用 steady clock。5 包 Jazzy Release build 和4项 GridMap/A* endpoint 用例通过。#315 与 #314 使用相同配置、障碍 SDF 和墙面相位，运动样本并非精确回放；观察到22个失败日志簇（中位间隔1.009 s）、20次 GEN_NEW_TRAJ 自循环、199次 A*调用，基线#314为20,385次。planner-only 探针仍收到2个不同ID的 spline，没有执行轨迹、控制/PX4、truth 或同刻occupancy snapshot。

决定：保留0028为实验补丁，不修改 `src/vendor`、不进入 canonical dependencies、不更新通过状态。下一步给 spline 接收事件加只读 occupancy snapshot 观测，并离线检查曲线采样的 unknown、inflation mask与机体包络；直到精确时序和净空证据具备前，不将B-spline视为避障通过。
