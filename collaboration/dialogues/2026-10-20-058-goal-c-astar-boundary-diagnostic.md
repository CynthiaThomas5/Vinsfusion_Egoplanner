# 任务对话摘要

- 日期与任务 ID：2026-10-20，#058；承接 #057 的 GOAL C unknown-policy 隔离诊断。
- 用户目标与明确约束：继续单 D435i 仿真 P0–P6；旧来源与 `src/vendor/ego_planner` 保持只读；不改变唯一 PX4 控制发布边界；unknown、无效深度和视野外空间不得默认 free；保留现有工作区修改，不 stage、commit 或 push。
- 实施决定：仅在 #297 重建源的临时副本中按 0020、0022、0023 顺序测试；第三方诊断补丁和 0.5 m inflation 不接入 canonical 依赖、默认配置或闭环组合。ASan 保留在规划核心，`traj_utils` 用 `EIGEN_MALLOC_ALREADY_ALIGNED=0` 编译以统一跨库 Eigen 分配路径。
- 已确认：#03 的 ASan bad-free 来自 sanitizer 与普通 `traj_utils` 的 Eigen 对齐宏不一致，兼容重建后 ROS Python import smoke 通过。#04 的 ASan 堆越界读位于 `BsplineOptimizer::initControlPoints`，源码会在减小 A* 下标后、重新检查边界前访问路径向量。新隔离补丁 0023 保护该函数的两处路径遍历；#06 运行记录了三次边界退出且未生成 ASan 报告。
- #06 目标前定位与 MapStatus 均 ready，随后发送 `(2.5, 1.4, 1.0)` 目标。首控制点障碍诊断 13 次均显示 `in_map=1, unknown=1, getOccupancy=0, inflated=1`；另有 288 次 A* 池边界／起终点拒绝、38 次方向失败，未生成 B-spline。目标后的只读快照请求被 `depth_pose_gate_closed` 拒绝。该轮只确认代码缺陷和失败特征，不是规划或 GOAL C 验收。
- #05 因 `propagated_stale` 未满足目标门而排除；为 #06 将诊断采样窗口从 30 秒延至 55 秒，未放宽发布目标的 readiness 条件。
- 后续待办：核对 A* 坐标到索引的转换与 active local-pool bounds；在深度／位姿门关闭前留存同 epoch/map_id 快照；再次分开判断 unknown 阻塞与越界端点。GOAL C/D/F 保持 pending。
- 证据：[`progress/evidence/p2-ego-rebound-warning-diagnostic-20261020-307.json`](../../progress/evidence/p2-ego-rebound-warning-diagnostic-20261020-307.json)。
