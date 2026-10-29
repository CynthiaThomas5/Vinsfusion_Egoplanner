# N10.3/#414 ROS 构建

- **命令：** `bash tools/project.sh build ros`
- **结果：** 17/17 包通过，包含 `plan_env`、`ego_planner` 和 `uav_px4_bridge`；EGO 安装产物 SHA-256 记录在相邻 JSON。
- **诊断：** 只出现既有 deprecated `ConstPtr`、unused parameter、VLA 编译警告，无 error。
- **范围：** 这是 #414 校准的增量 ROS build，不是 N10.5 隔离 clean fetch/build。尚未启动 SITL。
