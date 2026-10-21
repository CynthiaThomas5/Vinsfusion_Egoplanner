# 单一参数来源

- `runtime.json`：固定镜像ID、ROS域、PX4标准构建路径、出生位姿及构建并行度。
- `components/localization/`：固定双目VINS与健康门；`vins_runtime.json`当前OpenCV4线程。
- `components/mapping/`：深度配对、体素地图及EGO参数；默认0.5m/s／0.8m/s²、40×40×6m、膨胀0.5m（PROVISIONAL）。
- `components/navigation/room_crossing_goal.json`：相对16m任务，native停止0.1m，独立评估0.25m、yaw0.35rad、驻留1wall s；任务deadline180wall s。
- `components/px4_bridge/`：唯一控制桥／时间／坐标／EV配置；`flight_limits.json`的上升cap0.3m/s由参数生成器自动并入VIO airframe，下降与落地使用PX4默认值。
- `components/simulation/`：传感器桥及IMU落稳判据。debug_truth桥仅用于调试组合。
- `rviz/`：显示模板，按新VINS epoch生成每次运行的固定坐标帧。

相机内外参从`simulation/models/d435i/model.sdf`生成，PX4杆臂从x500安装SDF派生；不维护第二份外参。运行产物只记录当次配置和哈希，不作为下一次默认输入。实机标定与正式安全阈值仍待验收。
