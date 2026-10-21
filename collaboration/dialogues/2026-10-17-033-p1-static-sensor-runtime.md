# P1 固定 D435i 传感器链运行复核

- 用户目标：继续完成 `GOAL.md` 全部 A–H 与 P0–P6；本轮 P0 后转入 P1，不缩窄为单一 P4 问题。
- 约束：使用项目固定镜像与新全仓 install；旧仿真容器保持运行；隔离 ROS domain 与 Gazebo partition；只读传感器验收，不发布控制；完整保留失败尝试。
- 运行：新 disposable container 使用 ROS domain 229、专用 Gazebo partition，启动固定 D435i 校准世界并运行 `tools/check_sensors.py` 15秒。
- 结果：31/31项通过，验证双目／配对、RGB、深度与米制平面、CameraInfo、IMU、clock、单调 stamp、几何视差和固定 TF。P1 阶段据此标为通过；软件渲染因子约0.68x，RGB/深度按仿真 stamp 约25.37/13.35 Hz。
- 排除运行：domain 242 超出 Fast DDS 端口范围，节点未开始采样；日志保留在 artifacts，未计入验收。
- 待办：静态传感器模型结果不代表动态 VINS/飞行；下一步重复 P2 力驱动 VINS 平移与转弯冷启动校准并评估健康门控。
- 对应证据：`progress/evidence/p1-static-sensors-runtime.json`；改动记录 `progress/changes/2026-10-17-033-p1-static-sensor-runtime.md`。
