# P2 定位适配与真实回放

- 用户目标：继续按 GOAL.md 推进整个单 D435i 仿真导航目标；保持 P0–P6 和 A–H 范围，不降低完成标准。
- 约束：旧项目只读；本阶段仅单相机 P2；真值只供隔离评估；定位适配不得发布 PX4 控制；每个 VINS 会话使用新 epoch；不把结构检查或单次回放当阶段通过。
- 决定：新增类型化 LocalizationStatus 和定位适配器。无飞机安装外参时只输出 epoch 隔离的 D435i IMU frame；不发布 `base_link` 或 TF。VINS 健康由外部暂定门槛评估，失效锁存且需新会话恢复。
- 验证：Jazzy 容器构建 `uav_interfaces`、`uav_sim`、`uav_localization`；8 项纯逻辑测试通过。真实 VINS 从运动一致 MCAP 冷启动回放后进入 TRACKING，观测优化约15.15 Hz、传播200 Hz；录包数据停止后状态 LOCKED。另做一次 VINS 停止并在相同 epoch 重启注入；适配器仍 LOCKED，重启后3秒只读探针未见新增里程计。
- 输入 MCAP 包含 `/clock`、D435i IMU、左右红外图像，不含真值；适配器及探针订阅图不含真值。
- 开发中发现并保留适配器启动超时、Jazzy MessageInfo 元数据和 DDS endpoint identity 的失败尝试；最终实现读取 ROS graph endpoint，并核验同一节点身份与每 topic 各自的 GID。
- 待办：健康数值仍 PROVISIONAL；重复独立校准、双目／IMU／深度断流、第二次 VINS 重启、endpoint 替换、时钟回退、深度地图／EGO／PX4／EKF2 均未验收。维持所有阶段未通过。
- 对应改动记录：progress/changes/2026-10-16-007-p2-localization-adapter.md。
