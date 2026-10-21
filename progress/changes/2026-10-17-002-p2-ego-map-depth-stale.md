# P2 动态深度 stale 与 EGO 地图 reset

- 关联对话：[任务摘要](../../collaboration/dialogues/2026-10-17-002-p2-ego-map-depth-stale.md)。
- 文件与行为：未修改自维护代码或 canonical 仿真配置。新增两组 run artifact 与 test-only launch wrapper，通过 ROS remap 将仿真深度接入既有 source-stamp fault relay；新增轻量证据报告，并更新 CURRENT、milestones、GOAL checklist、依赖来源证据链接和接口状态。
- 动态验证：run #02 和 #03 使用独立 ROS domain、Gazebo partition 与 VINS epoch。relay 分别丢弃 71 和 148 帧，均观察到前传／丢弃／恢复前传；健康状态转 `depth_stale` 后回 READY。adapter 确认新的 map_id reset；占据点分别从最高 1,405／1,439 清零，再在同一 epoch frame 重建。证据和日志哈希见[验收报告](../evidence/p2-ego-map-depth-stale.json)。
- EGO 局限：两次均观察到 EGO 起步规划成功；但 depth stale 窗口到来前 FSM 已回到 WAIT_TARGET，日志没有 `Depth Lost` 或 `EMERGENCY_STOP`。没有 PX4、trajectory server、controller 或控制发布者。
- 排除项：run #01 的 test-only LaunchService runner 错误地传递 source object，传感器 launch 未成功，记录在报告但不计通过。前一 EGO shutdown 诊断脚本遗留的传感器组也在此次复查中停止，之后没有活动测试节点。
- 局限与下一步：两次只验证 stale gate、map 清理和恢复，不代表飞行响应或地图精度验收。下一步把 stale 注入安排在 EGO 活动轨迹期间；随后验证 VINS epoch 切换、时钟回退对旧地图和旧样本的隔离，并补充快照回读。
