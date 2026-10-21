# P2 双目断流与时钟速率门控

- 用户目标仍是按 GOAL.md 完成单 D435i 仿真导航全链路；本轮只推进 P2 故障门控，不缩减 P0–P6／A–H 范围。
- 约束：旧项目只读；最终定位不得依赖真值；定位适配器不发布控制；每次回放使用新 epoch；记录实际验证及无效尝试，P2 继续保持 in_progress。
- 调查发现：慢速 bag 回放下，固定墙钟接收超时会在源时间仍新鲜时先锁定；`rosbag play --clock` 生成的接收时间时钟也会和消息内仿真时戳不一致。
- 决定：将接收年龄按观测 ROS 时钟速率折算成仿真秒；六路源时戳年龄及稳态墙钟停钟检测仍单独生效。故障中继按消息 header stamp 排程，探针保存 ROS 时钟和墙钟转换时间。回放含 `/clock` 时直接重放该话题，不传 `--clock`。
- 验证：新增9项健康逻辑测试通过；Jazzy 新目录构建 `uav_interfaces`、`uav_sim`、`uav_localization` 通过。两次独立双目断流回放都在 TRACKING 后丢弃左右红外图像各31帧，分别于源时钟2.779／2.781秒以 `left_stale` 锁定；图像在3.532秒恢复转发，同一 epoch 未重新 TRACKING，输出计数未增长。
- 证据：[双目断流报告](../../progress/evidence/p2-stereo-dropout.json)，原始数据和日志位于 `artifacts/runs/p2-localization-stereo-drop-20261016-13/` 与 `...-14/`。
- 无效尝试：保留了未观察到 TRACKING、墙钟与源时间无法对齐、误用 rosbag `--clock`、以及旧接收门槛在故障窗口前锁定的运行；均未计入两次通过数。
- 待办：仅双目故障达到两次。IMU／深度断流、第二次 VINS 重启、规划器退出、时钟回退等仍未满足 GOAL.md E；健康阈值仍 PROVISIONAL，P2 与整体 Goal 均未通过。
