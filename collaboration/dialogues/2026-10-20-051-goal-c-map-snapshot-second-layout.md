# GOAL C 第二障碍布局同 epoch 快照 #295

日期：2026-10-20

## 任务摘要

在 #294 的基础上把箱体与圆柱改到另一组位置并调整尺寸，保留墙面和力驱动传感器运动，验证第二布局的同 epoch 三时刻占据快照及离线SDF几何比较。

## 约束与决定

- 只运行 D435i/VINS、定位/深度健康与 mapping adapter、隔离 EGO `plan_env`；不启动PX4、controller、traj_server或目标。
- 使用新ROS domain、Gazebo partition与VINS epoch，复用#292已构建的候选安装；不修改`src/vendor`或canonical sources。
- 运行时无truth/control topic；fixture truth独立保存，仅离线用于一次固定尺度轨迹对齐。
- 单次第二布局的快照不能代替同场景独立重复或冻结指标；GOAL C继续 pending。

## 结果与后续

三份快照身份一致，known voxel数17,478→21,677→21,983；occupied集合Jaccard为0.601/0.683。每轮occupied体素中心到同场景SDF距离最大8.58 cm。墙面区域中位体素中心在两个时间间隔分别移动7.33和7.12 cm，约一个栅格；这是描述性变化，不足以判定ghosting。EGO未见odom/depth lost告警，但没有目标，规划未测试。

下一步以新epoch独立复测第二布局，审查墙面位置变化，再确定ROI覆盖和ghosting测量标准。权威结果在progress/evidence及运行报告，本摘要不是测试通过凭证。
