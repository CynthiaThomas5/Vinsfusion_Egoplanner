# ROS 源码布局

own 是自维护包，vendor 是固定上游版本。当前 own/uav_sim 已实现传感器仿真与静态校准启动；own/uav_interfaces 提供定位、深度健康和地图 reset 接口；own/uav_localization 已实现会话绑定、健康门控与 IMU-frame 里程计适配，并通过真实 VINS 输入回放；own/uav_mapping 已将深度健康门和源时间位姿适配接入唯一 EGO `plan_env` 地图实现。合成 smoke 验证了定位失效清图；动态 D435i/VINS run 验证了占据点输出随运动更新，但未分析地图点几何或规划器响应。uav_navigation、uav_px4_bridge、uav_bringup 仍是设计骨架。vendor 中固定提交 VINS 的 camera_models 与 vins 已在 Jazzy 实际编译。完整导航系统尚未实现。

模块说明见各 own 子目录 README 和 docs/directory-layout.md。未来从项目根目录构建，build／install／log 在根目录并被忽略。仿真资源与参数只引用 simulation 和 config 的唯一来源。
