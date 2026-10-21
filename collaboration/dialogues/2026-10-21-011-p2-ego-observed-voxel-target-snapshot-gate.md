# GOAL C pitch 后真实 3D 目标与快照门诊断 #344

用户要求继续完成 `GOAL.md`。本轮按仓库约定保留已有改动，只推进单 D435i 仿真导航；unknown保持fail-closed，唯一PX4控制发布者仍为`uav_px4_bridge`。实验只运行 planner-only EGO，没有真值输入、PX4、controller、trajectory server或控制话题。

决定与边界：使用新 ROS domain 和 epoch，以 `/navigation/ego_goal` 的 `NavigationCommand` 发送真实 3D 目标 `[0.25,-0.15,0.4]`，复用#341 run-local EGO overlay及实验补丁0033，不改canonical/vendor源码，也不放宽0.4 s freshness门。

结果：pitch前后同epoch/map_id快照显示目标voxel `[122,118,5]` 从unknown变为free/uninflated，known voxel数8034→25341。EGO收到目标后输出目标候选样条，depth loss后又输出急停样条。两条样条各15次只读快照请求均未取得可接受snapshot，记录28次`depth_pose_gate_closed`与2次`no_fresh_fused_depth`。EGO depth/pose sync计数停在932，最后同步now为35.859 s，首次timeout为36.268 s；上游MapStatus和定位状态仍ready，但不能由此推断EGO reader新鲜。

结论：#344作为排除的时序门诊断，不对曲线作occupancy、碰撞或净空判定，不计作GOAL C证据。下一步对齐EGO depth/camera-pose reader receipt、QoS和同步器时间戳与adapter输出；保持freshness阈值和unknown策略不变。样条时刻可读快照恢复后再做第二布局、扫掠体积与安全视角合同审查。
