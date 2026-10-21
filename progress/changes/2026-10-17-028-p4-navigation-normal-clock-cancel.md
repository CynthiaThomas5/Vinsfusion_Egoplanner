# P4 正常时钟 caller-cancel 与空闲关闭

- 任务 ID／日期：2026-10-17-028。
- 对话摘要：[2026-10-17-028-p4-navigation-normal-clock-cancel.md](../../collaboration/dialogues/2026-10-17-028-p4-navigation-normal-clock-cancel.md)。
- 修改文件：#58 run-private wrapper、运行输入与产物；`progress/evidence/p4-navigation-shutdown.json`、`progress/evidence/README.md`、`progress/CURRENT.md`、`README.md`、本记录和对话摘要。没有改生产代码或正式配置；P4 仍为 `in_progress`。
- 运行结果：固定 Jazzy build #32、ROS domain226、新 Gazebo partition，使用 canonical `/clock` 单 publisher，未启动 relay。新 epoch 下定位处于 TRACKING、初始优化里程计年龄23.2 ms、深度健康有效、最近 pose/depth 配对年龄19.5 ms、地图非空。请求位置约(1,0,0.8)m及 yaw=0.7 rad，EGO 发布同 goal/epoch B-spline（yaw终值0.7）与 READY；READY的 command age为36 ms。caller-cancel被接受，action为 `canceled/caller_cancel`，traj_server对同 goal/epoch发布ABORT，ABORT后READY为0；终态后导航保持存活，空闲SIGINT后退出码0。
- 限制：运行中 EGO 先有3条 odom/depth timeout日志和10条优化器错误，随后才成功规划一次。该短运行没有跟踪轨迹、测量到达或避障，也不是重复验收；正常时钟活动目标SIGINT仍待执行。
- 验证：run wrapper退出码0；canonical `/clock` publisher数1、`/clock_raw`不存在；node list及 `/fmu`审计未发现PX4控制节点或话题。目标、轨迹、cancel、action结果及相关日志按 SHA-256 保存在 #58 manifest。语法、项目结构、哈希和 diff 检查在本轮最终验证中记录。
- 下一步：正常时钟下发送目标并在匹配 READY 后对活动导航节点发SIGINT，验证 action与traj_server均ABORT、无后续READY且干净退出。输入timeout与executor CPU原因未明，不放宽门控；轨迹跟踪／到达、多场景、10分钟负载、PX4闭环与其他 GOAL 项仍待完成。
