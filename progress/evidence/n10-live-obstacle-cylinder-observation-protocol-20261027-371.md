# N10.3/#371：静态圆柱接触处的只读观测补齐

## 假设与唯一变化

#369 曾记录与静态 `unit_cylinder_4` 的机体接触。接触时 EGO 命令参考到圆柱轴线约 0.962 m，固定 SE(3) 对齐后的真值 IMU 点与命令参考相差约 0.519 m；接触附近没有保存 D435i 图像、圆柱区域 EGO occupied-cloud 或地图查询。#371 补齐这些只读数据，以区分“深度/occupied 输入包含圆柱”与“命令到真实机体的偏差消耗净空”两种可能贡献。

按用户要求，先移除 `vio_ego_bringup.py` 中四项本项目自加 N05 数值几何拒绝条件：机体半径内部等式、终端保持半径 1 m 上限、地图底边覆盖机体球关系、规划 inflation 与包络半径相等关系。它们不是上游 EGO 碰撞算法；保留参数有限值/非负格式检查。#371 当前配置本来满足已移除关系，故 planner 参数和本次实际启动值不变。导航、地图身份/时效完整性、唯一 PX4 控制桥、EGO 原生碰撞语义、任务、spawn、世界、方箱及注入时刻仍按冻结输入。另只调整 run-local 只读 observer。观察器不发布控制，不使用真值触发或控制，不修改地图或 PX4 状态。

## 采样协议

- 方箱仍在 goal source stamp 后 12.0 仿真秒请求创建，需先收到 Gazebo ACK，并保持 #369 的目标、planner 与桥控制路径。
- 注入之后，当同一 goal/epoch 的 EGO `PositionCommand` 首次进入 SDF 圆柱轴线的 1.6 m 水平范围，启动观测窗。
- 记录 `/drone_0_camera_pose`，并在窗口 0.0、0.4、0.8、1.2、1.6 仿真秒附近保存 `/sensors/d435i/depth` 与 `/sensors/d435i/color/image_raw`。每帧附带最新相机位姿和 frame/stamp/hash。
- 每第十个 EGO `/grid_map/occupancy` 消息计算一次圆柱 ROI 点数与半径 0.5 m 表面壳点数，并记录 frame、消息戳及位置假设。
- 在 approach 与 near-pass 各请求一次半径 0.30 m 的 `QueryOccupancySphere`，使用 goal 时锁定的相同 epoch/map_id；请求和响应都存档。raw 查询的 unknown/拒绝按原样记录，不触发控制。
- 完整记录位置命令、planner spline、VIO/桥接、debug truth、机体接触和终态 PX4 读回。固定真值只用于离线复算，不进入导航。

## 判据与停止

本实验是 N10.3 诊断，不是 N10/N12 资格。结果用于判别观察链路与偏差，不修改 GOAL F 的 ≤0.30 m、≤15°、≥3 s，也不把接触从失败中剔除。无圆柱 ROI 样本、缺地图身份、未观察到相机位姿、评估时间覆盖不全，均标为缺数据。任何实际接触仍是接触失败。

只有 runtime contract、run-local 工具哈希、EGO graph、Gazebo create、action-cancel 和所有接触传感器通过运行前检查后才发送目标。结束后需确认完整观察器终态，以及 PX4/bridge landed、disarmed、control disabled、零控制样本，之后才能停止该项目容器。预检失败时不飞行；任务结果失败时保留归档。

## 冻结身份

- Run ID：`n10-20261027-371-cylinder-observation-live-obstacle`
- Runtime contract：`9c2f704da0904fabe62925d8526f529c13ce9fbc5ed058d5cf91be9479b6ede6`（665 项；与 #369 的差异限于上述项目自加检查删除及其重建产物）
- Bridge module SHA-256：`cf9f0056c9a8f7f0b9b0f224613591d77249d1647707b5d1ac0e5165a1d870ab`
- Protocol SHA-256：`1b99c39c2f88a9b25c23671a09df48ab7bd024f6c41235218a4b4388a0d187a5`
- Run-local tool freeze：[JSON](../../artifacts/n10-prepared/n10-20261027-371-cylinder-observation-live-obstacle/n10-tool-freeze.json)
- Prelaunch identity：[JSON](n10-live-obstacle-cylinder-observation-prelaunch-20261027-371.json)

验证：`python3 tools/test_vio_ego_bringup_config.py` 10/10 通过；`bash tools/project.sh test` 415/415 通过；`bash tools/project.sh build ros` 17 包通过；运行源码与安装模块 SHA 一致。语法检查使用独立 `/tmp` pycache 成功，避开仓库内 root-owned 的旧缓存目录。

当前状态：移除项目自加数值拒绝条件后的 protocol/runtime/tool identity 已重新冻结；SITL preflight 尚未完成，尚未发送目标。
