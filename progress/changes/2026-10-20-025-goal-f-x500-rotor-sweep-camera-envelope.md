# GOAL F D435i 外壳与旋翼扫掠包络复核

关联对话：[2026-10-20-025](../../collaboration/dialogues/2026-10-20-025-goal-f-x500-rotor-sweep-camera-envelope.md)。

在自维护 `simulation/models/d435i/model.sdf` 中加入名义 D435i 外壳碰撞盒（X/Y/Z = 25/90/25 mm），尺寸来源及朝向假设见 [仿真资源说明](../../simulation/README.md)。没有修改只读 PX4 源码。

更正 #245 的机体半径解释：旧计算使用旋翼碰撞盒默认角度。PX4 x500 SDF 将四个碰撞盒附着在 Z 轴旋转关节上；新的可复核脚本对每个矩形碰撞盒计算完整扫掠圆盘。相对 `d435i_imu` 原点，模型水平半径为 0.4815 m、方向不变球半径为 0.4819 m。#245 保留为历史记录；0.099 m 膨胀在 0.1 m 网格仍仅 1 步，配置保持 PROVISIONAL。

验证：

- `gz sdf -k simulation/models/d435i/model.sdf`：有效；仅有原有 `gz_frame_id` 扩展警告。
- 固定 `d435i-vins:dev` Jazzy/Harmonic 环境启动项目传感器校准场景，`tools/check_sensors.py --seconds 15`：31/31 通过，双目、CameraInfo、深度、IMU、时钟和 TF 均收到。
- `python3 artifacts/runs/p0-d435i-footprint-20261020-246/audit_vehicle_envelope.py` 与 `py_compile`：通过；计算输入和输出哈希见 [证据报告](../evidence/p0-d435i-footprint-20261020-246.json)。
- `python3 tools/project_status.py`、`git diff --check` 与 `git diff --cached --check`：通过。

局限：传感器回归使用静态校准 fixture，不含 x500、规划器、控制、真值或碰撞接触试验。盒体不含安装支架、线缆和公差；模型包络不含地图／定位／跟踪误差、数据年龄或制动距离，故不能冻结最小净空。下一步测量多障碍地图几何以及同运行定位、跟踪和制动基线，再推导完整 GOAL F 标准。
