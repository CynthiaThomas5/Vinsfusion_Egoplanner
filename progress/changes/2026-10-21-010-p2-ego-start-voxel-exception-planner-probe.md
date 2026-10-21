# GOAL C 实际 3D 目标与起点 unknown voxel 实验守卫 #343

## 结果

沿 #338 的 pitch 后 known-free 栅格路径，在独立 ROS domain 用 EGO 实际订阅的 `/navigation/ego_goal` `NavigationCommand` 发出 epoch 绑定 3D 目标 `[0.25, -0.05, 0.1]`。#340 的 `t=0` 拒绝仍是有效起点证据；#341/#342 使用的旧 `/move_base_simple/goal` 回调把高度固定为1 m，因此不作为本低位目标的非零拒绝结论。#343 使用 #341 run-local Release overlay（二进制 SHA-256 `71317092…d5b974e`），收到1条匹配 goal_id/epoch 的 B-spline。

对实际 knots/control points 用独立 de Boor 实现，按 EGO 源码的完整活动时间区间每10 ms采样并包含端点。42个样点中，31个仍在当前起点 `[120,119,1]` unknown voxel，11个在 known-free voxel；未采到 occupied、inflated 或地图外位置。独立读回的同 epoch、map_id、frame 栅格快照显示请求目标 voxel `[122,119,2]` known-free 且未膨胀。样条只到达局部端点，距请求目标约0.143 m。

这次仅在实验补丁0033下通过：它只放行完整曲线最初连续留在当前起点 unknown voxel 的部分，离开后仍阻止 unknown。快照服务返回时刻比 spline start 晚139 ms，深度源龄73 ms，故是近时同身份复核，不是规划器内部同字节地图证明。没有 trajectory server、controller、PX4、真值或控制话题；曲线未执行，中心线也不等于机体扫掠净空。

## 验证

- `python3 -m py_compile artifacts/runs/p2-ego-start-voxel-exception-planner-probe-20261021-343/analyze_spline_snapshot.py`：通过。
- `python3 artifacts/runs/p2-ego-start-voxel-exception-planner-probe-20261021-343/analyze_spline_snapshot.py`：8项身份、快照、起点未知体素范围、占据／膨胀／地图边界与运行图隔离检查通过。
- #341 的五包 Release overlay 构建此前通过并由 #343 复用；本轮没有改动或重建 canonical/vendor EGO。
- 结构任务将运行 `python3 tools/project_status.py`；GOAL C 保持 pending。

证据：[轻量报告](../evidence/p2-ego-start-voxel-exception-planner-probe-20261021-343.json)，原始快照、目标结果、分析器和 run manifest 位于 `artifacts/runs/p2-ego-start-voxel-exception-planner-probe-20261021-343/`。实验补丁及来源顺序记于[依赖说明](../../dependencies/README.md)。对话摘要：[2026-10-21-010](../../collaboration/dialogues/2026-10-21-010-p2-ego-start-voxel-exception-planner-probe.md)。

## 下一步

先量化起点周围名义机体包络内 unknown 的比例与范围，再换一组障碍布局、保持正确 3D goal 接口复测 planner-only，并尽可能收紧 spline 与只读 snapshot 的时间差。只有完整 swept-volume 检查和相机 pitch 机体安全合同通过后，再进入唯一 `uav_px4_bridge` 的 SITL 动作；不全局清 unknown，也不把0033带入 canonical依赖。
