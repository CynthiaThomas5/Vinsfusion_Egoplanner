# P1 固定 D435i 传感器链运行复核

- 任务 ID／日期：033／2026-10-17
- 对话摘要：[P1 D435i 运行复核](../../collaboration/dialogues/2026-10-17-033-p1-static-sensor-runtime.md)
- 修改文件：新增 P1 运行证据与 artifacts run manifest；更新 `progress/CURRENT.md`、`progress/milestones.json`、`progress/goal-checklist.json`、证据索引及 README 状态。
- 行为变化及原因：将 P1 标为通过。固定校准世界运行检查覆盖 GOAL P1 要求的单 D435i 双目、相机 IMU、RGB、深度、CameraInfo、clock、TF、几何、单位与同步。
- 验证类型：固定镜像容器内的 live sensor runtime 与静态检查；ROS 2 Jazzy、Gazebo Sim 8.14.0、最新17包全仓 install。
- 命令与环境：`ros2 launch uav_sim sensors.launch.py project_root:=/workspace`；`python3 tools/check_sensors.py --project-root /workspace --output .../sensor-report.json --seconds 15`；ROS domain 229、独立 Gazebo partition、软件渲染。
- 结果及证据位置：[P1 运行报告](../evidence/p1-static-sensors-runtime.json)，15秒 probe 中31/31项通过，双目配对308组，深度中值约2.99985 m；仿真时间/墙钟约0.68，RGB/深度约25.37/13.35 Hz。
- 失败尝试：`p1-static-sensors-20261017-01` 使用 domain 242，Fast DDS 在采样前拒绝启动；原始日志保留并作为排除运行。
- 未验证与限制：静态理想模型而非动态 VINS/机载外参；真实相机行为、VINS 误差、mapping、PX4、飞行均未由此验证；F 验收阈值未冻结。
- 下一步：重复独立 P2 力驱动 VINS 平移／转弯冷启动校准与退化门控，再冻结定量阈值。
