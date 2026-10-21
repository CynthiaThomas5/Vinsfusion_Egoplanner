# GOAL C 起点 unknown voxel 与真实 3D EGO 目标探针 #343

用户要求继续完成 `GOAL.md`。按仓库约定保留已有工作，只推进 P0–P6 单 D435i 仿真导航；unknown 保持 fail-closed，只有 `uav_px4_bridge` 可发布 PX4 控制，真值限定在隔离 `debug_truth`，本轮不接真值或控制。

决定与边界：#340 的 `t=0` 起点拒绝有效；#341/#342 的 `/move_base_simple/goal` 会把高度覆盖为1 m，不适用于低位 3D 目标。#343 改用 EGO 实际接收的 `/navigation/ego_goal` epoch 绑定 `NavigationCommand`，并复用 #341 run-local EGO overlay 和实验补丁0033，不改 canonical/vendor 源码。

结果：定位与 map ready 后发出 `[0.25,-0.05,0.1]` 目标，planner-only EGO 产生1条 B-spline。对完整活动时间区间按10 ms采样42次：31点位于当前起点 unknown voxel `[120,119,1]`，11点已知空闲且未膨胀；没有 occupied/inflated/越界点。快照同 epoch/map_id/frame，但晚于 spline start 139 ms。目标 voxel known-free；首条局部 spline 端点距请求点0.143 m。无 trajectory server、controller、PX4、truth/control graph，也没有机体净空或执行证据。

决定：0033只保留为隔离实验，unknown 仍默认阻塞。下一步量化当前起点周边机体包络中的 unknown，再做第二布局真实3D planner-only复测和更紧密的 spline/snapshot配对；扫掠体积和相机姿态安全合同通过前不运行PX4动作。
