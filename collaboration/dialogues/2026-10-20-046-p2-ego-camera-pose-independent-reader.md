# P2 EGO camera-pose independent-reader trace #290

用户要求继续推进 `GOAL.md`。本轮遵守项目边界：不修改旧来源、不改 `src/vendor`、不启动 PX4/控制器、不订阅真值、不调整健康门或验收阈值。

## 本轮决定

- 在 #289 的隔离仿真/EGO 构建上增加一个低带宽 reliable `PoseStamped` reader，仅记录 `/drone_0_camera_pose` 的主机收包时刻、单调时钟、header stamp 与 frame。
- 与 EGO `odom or depth lost` 日志按主机 realtime 对齐；保持 planner-only，不观察深度图，避免添加高带宽订阅。
- 不把额外 reader 收包解释成 EGO 自己收到了相同样本；不把轨迹 spline 当作执行或避障通过。

## 已确认结果

- #290 收到 1,264 条相机位姿，70 个 1 Hz observer heartbeat，source stamp 单调递增；全轮最大主机收包间隔 0.217 s，最大 header-stamp 间隔 66 ms。
- EGO 有 32 条输入同步超时，分成两簇。两簇内 EGO `depth_pose_sync_count` 分别冻结于 956、1121，`last_sync_in_map=true`；独立 observer 在同窗口持续收到相机位姿，最大 source-stamp 间隔仍为 66 ms。
- 两簇均早于定位因 `normalized_cost_exceeded` 关闭 mapping gate。该结果减弱 publisher-wide pose outage 假设，但未区分 EGO pose reader、depth reader 或 `message_filters` 配对。
- planner-only目标已派发并捕获98条 B-spline；无 PX4/control 节点与话题、无真值输入，trajectory 未执行。
- host clock monitor 覆盖85.70秒，realtime-minus-monotonic范围20.6 μs，未见明显回拨。
- 复核启动脚本发现 #290 实际复用了 #289 的 `ROS_DOMAIN_ID=136` 与 Gazebo partition；两轮顺序运行，且 #290 启动前无项目容器/节点，但没有跨domain隔离。证据元数据已更正；不能排除共享domain环境影响。
- observer SIGINT 终止时写入 stopped marker 和全部样本，之后 `rclpy` 输出 `ExternalShutdownException` 与重复 shutdown 错误。数据窗口仍完整；observer 清理代码需在后续复用前修正。

## 待决问题

- EGO 自身的 pose/depth `message_filters::Subscriber` 回调是否在这些超时窗继续收到数据？
- 若两个 filter 输入都继续收到，近似时间队列是否匹配；若只有一侧停顿，哪侧首先停顿？
- GOAL C 的 unknown安全语义、地图覆盖与自由空间仍未验收；P2阶段通过不代表 GOAL C/D/E/F 或 P6 通过。

证据：[轻量报告](../../progress/evidence/p2-ego-camera-pose-independent-reader-20261020-290.json)；运行原始数据在 `artifacts/runs/p2-ego-camera-pose-observer-20261020-290/`。
