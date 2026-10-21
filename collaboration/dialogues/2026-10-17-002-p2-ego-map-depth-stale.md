# P2 动态 depth stale 与 map reset

- 继续推进 `GOAL.md` 全部 A–H、P0–P6；本次不改变范围，不启动 PX4 或控制发布者。
- 用 source-stamp relay 通过测试专用 launch remap，把 Gazebo 深度先送到 `/fault/input/depth`，再恢复发布到现有 `/sensors/d435i/depth`；canonical bridge YAML 和相机参数没有修改。
- 两次新 ROS domain、Gazebo partition 和 VINS epoch 运行均观测到定时深度丢弃，depth health 转 `STALE` 后回 `READY`。`mapping_input_adapter` 收到 stale 后调用 plan_env reset，生成新 map_id；动态点云采样曾归零，输入恢复后在同一 epoch frame 重新生成。
- 两次运行各启动 EGO 和非零 preset 目标，期间规划成功数次；但 stale 到来时 EGO 已回到 `WAIT_TARGET`。结果只证明 adapter/map 清理与恢复，不证明活动轨迹保护、goal 状态或 PX4 故障响应。
- 初次测试专用 launch runner 用法错误的 run #01 保留并排除；修正 runner 后的 run #02、#03 计入。另复查发现前一停机诊断误清空 sensor launch PID 列表，遗留组已停止。
- 下一步让注入窗口覆盖 EGO 活动轨迹时段，随后检查 epoch 切换与 ROS clock 回退是否清图并阻断旧样本。
