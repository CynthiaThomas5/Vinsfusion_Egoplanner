# 2026-10-30 #603 RViz 第一视角相机

## 任务摘要

用户希望 RViz 能显示无人机的相机第一视角，并在 EGO 按路线穿过柱群碰撞体时观察该视角；当前 Orbit 视图看起来像第三人称。沿用已接入的 NavRL 柱群场景及 GUI 会话。

## 用户约束与既定范围

- 保留已确认的柱群场景、碰撞地图和已落地的 PX4/Gazebo 会话。
- 当前任务只调整只读可视化，不改 EGO 规划、地图输入或 PX4 控制输出。
- 以真实 D435i RGB 相机画面为第一视角；碰撞历史、inflated 地图和 EGO 路线作为辅助叠加层。

## 本轮决定

- RViz Camera display 需要 CameraInfo 与相机到地图 fixed frame 的 TF。当前 RGB/CameraInfo 有数据，但 `/tf` 与 `/tf_static` 没有发布者。
- 用已通过健康检查并发布的 `/localization/imu_odom` 和 `simulation/models/d435i/model.sdf` 派生相机可视化变换；TF 只供 RViz，不发布控制指令，也不订阅真值。采样检查发现 optimized 约 10 Hz、propagated 约 140–190 Hz，因此相机 TF 用高频传播输出以减少画面跳动。
- 以 `rviz_default_plugins/Camera` 显示前向 RGB 和当前 map/path 图层；保留可切回 Orbit 的碰撞地图视图。

## 待决问题

- 无。用户要求恢复试验前的 Orbit 视图并停止后续尝试。

## 结束决定

- 第一视角试验及柱群 16m 运行已完成记录。
- Camera display、RViz 浮动窗布局及 localization 可视化 TF 均撤回；当前 preset 恢复原始 Orbit 碰撞地图。
- 不继续相机布局或额外飞行。
