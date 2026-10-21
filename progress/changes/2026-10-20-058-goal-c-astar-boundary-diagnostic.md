# 修改与验证记录

- 任务 ID／日期：#058 / 2026-10-20
- 对话摘要：[ #058 对话摘要](../../collaboration/dialogues/2026-10-20-058-goal-c-astar-boundary-diagnostic.md)，承接 [#057](../../collaboration/dialogues/2026-10-20-057-goal-c-unknown-policy-wall-probe.md)。
- 修改文件：新增 EGO 隔离实验补丁 `dependencies/patches/ego/0023-init-control-point-astar-boundary-guard-experiment.patch`；更新 EGO patch provenance README；新增 #0023 源码／build manifest、targeted build report、运行脚本及 #03–#06 运行材料；新增 [#307 轻量证据报告](../evidence/p2-ego-rebound-warning-diagnostic-20261020-307.json)、更新 `progress/CURRENT.md` 和证据索引。没有修改 `dependencies/sources.json`、canonical source、默认参数、PX4 控制、`src/vendor/ego_planner` 或旧来源。
- 行为变化及原因：产品行为没有改变。#0023 只在临时第三方源码副本中为 `initControlPoints` 的 A* 路径向量访问增加边界检查和空路径检查，避免已被 ASan 复现的越界读，并记录边界退出。unknown-as-obstacle patch 0020 与 0.5 m inflation 仍仅用于诊断。
- 验证：
  - #0023 在 post-0022 disposable source copy 上 `patch --dry-run`、应用和反向 dry-run 均通过，CRLF 保持。
  - #307 初始 EGO 五包 build 通过；为避免 Eigen sanitizer 宏跨共享库不一致，`traj_utils` 以 `-DEIGEN_MALLOC_ALREADY_ALIGNED=0` plain rebuild 通过，ROS Python message import smoke 通过，库没有 `libasan`／`libubsan` 依赖。
  - `bspline_opt` 与 `ego_planner` 在应用 #0023 后分别重建／重链接通过；最终规划器仍链接 ASan/UBSan。
  - #04 ASan 确认 `bspline_optimizer.cpp:711` 发生堆越界读；#06 运行命中三次受保护的路径边界退出且没有 ASan 报告。
  - #06 目标就绪后发送手动目标，但首控制点位于 unknown cell；记录到 288 次 A* 池边界／起终点拒绝和 38 次方向失败，无 B-spline。目标后的 snapshot 以 `depth_pose_gate_closed` 被拒绝，不属于规划成功或地图快照证据。
- 结果及证据：报告状态为 `ASAN_CONFIRMED_ASTAR_VECTOR_BOUNDARY_READ; ISOLATED_GUARD_HIT; PLANNER_OUTPUT_AND_MAP_GATE_UNQUALIFIED`。证据报告 SHA-256=`8391f668d3f2eb9c0edc44570287af4b785849008cd7aefbf4472b5159861d62`；运行材料位于 `artifacts/runs/p2-ego-rebound-warning-diagnostic-20261020-307/`。
- 局限与未验证：#06 没有生成或执行轨迹，快照服务拒绝读回；unknown 阻塞与 A* 局部地图越界端点之间的因果比例未区分。没有 PX4、controller、trajectory server、在线真值或执行控制。GOAL C/D/F 与 P2 健康阈值状态不变；没有里程碑被标记通过。
- 下一步：只读核对 A* 坐标转换和 active pool bounds，并调整诊断采样顺序，在 freshness gate 关闭前捕获同 epoch/map_id snapshot；然后重复同目标，把 unknown-policy 与 out-of-map 端点分别验证。
