# P2 双目断流回放与时钟速率门控

- 任务 ID／日期：008，2026-10-16
- 对话摘要：[P2 双目断流与时钟速率门控](../../collaboration/dialogues/2026-10-16-008-p2-stereo-dropout.md)
- 修改文件：`src/own/uav_localization/uav_localization/health.py`、`tools/test_localization_health.py`、`tools/fault_relay.py`、`tools/test_fault_relay.py`、`tools/probe_localization.py`、VINS 调试说明、定位包说明、README、CURRENT、里程碑与回收清单。
- 行为变化：六路输入的接收年龄改为按 ROS 时钟观测速率折算为仿真时间；源时戳年龄和稳态墙钟停钟检测保留独立门槛。故障中继现在按源消息时间排程并报告丢弃／恢复的 stamp；探针记录状态转换的 ROS 时钟与墙钟。回放包含 `/clock` 时直接重放，不使用 `rosbag play --clock`。
- 验证命令：`python3 tools/test_localization_health.py`（9项通过）；Jazzy 容器执行 `python3 tools/test_fault_relay.py`（1项通过）；Jazzy colcon 构建 `uav_interfaces uav_sim uav_localization` 成功。具体构建日志及哈希见 [双目断流证据](../evidence/p2-stereo-dropout.json)。
- 回放结果：run 13 与 run 14 使用不同 epoch、同一运动一致传感器 MCAP、0.2 倍播放和新的定位安装目录。两次都观察到 TRACKING，左右图像于源时间2.502–3.502秒各丢31帧，锁定原因均为 `left_stale`；恢复转发由3.532秒开始，完整探针中无新优化／传播输出，epoch 未恢复。输入与探针均无真值话题。
- 保留的无效尝试：run 08 未观察到 TRACKING；run 09 的墙钟排程无法与源时钟对齐；run 10 的 `--clock` 造成 bag 接收时间与源图像时戳不一致；run 12 在故障窗口前因旧墙钟接收门槛以 `telemetry_stale` 锁定。四次数据均在 evidence 中标为无效，不纳入重复计数。
- 局限：只完成双目断流这一故障模式的两次调试回放。IMU／深度断流、规划器退出、第二次 VINS 重启和时钟回退仍待注入；健康数值仍是 PROVISIONAL，未通过 P2、GOAL.md E 或最终验收。
- 下一步：按同一源时钟与新 epoch 协议验证相机 IMU 断流；随后深度、规划器和时钟故障分别做两次独立注入，并继续 P0/P1 工作。
