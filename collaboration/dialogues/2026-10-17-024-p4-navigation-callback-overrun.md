# P4 导航回调空档与稳态 watchdog 诊断

- 任务：继续推进单 D435i P4 动态规划与活动任务关闭；调查导航 status/odometry freshness 间歇，并验证 ROS 仿真时钟停顿时 watchdog 是否仍运行。
- 用户约束：遵守项目 `AGENTS.md` 与 `GOAL.md`；旧实验区只读；不接 PX4 控制、不启动实机；保留已有工作树修改，不把构建或单次 live run 写成阶段通过。
- 实施：导航 freshness timer 使用 `ClockType.STEADY_TIME`，与 `time.monotonic()` 接收年龄同属墙上稳态时钟；goal 门控及 freshness 阈值未变。合成 action 测试新增 `use_sim_time=true`、持续 odometry、暂停 `/clock` 的 stale 故障场景。定位 freshness probe 补充绝对墙钟时间戳及 `/localization/optimized_imu_odom` 独立订阅。
- 静态验证：Jazzy 隔离构建 run #25 的 `uav_navigation` 通过；10 项任务核心测试和 action 合成测试通过，冻结 `/clock` 时约0.5秒后检测 status stale、ABORT 活动目标并清轨迹。
- live 观察：caller-cancel 在 #22/#26/#27 成功；#24 在规划后 `localization_status_stale` 中止。活动目标 SIGINT #29 通过，返回匹配 `navigation_node_shutdown` ABORT、traj_server 同 goal/epoch 清轨迹、无后续 READY、进程退出码0；但 status/timer/optimized-odometry callback gap 为3.258/3.242/3.316秒，teardown 有异步 Destroyable 异常。独立 adapted-odometry observer 最大 gap 189 ms；独立 status history 最大 gap 1.30秒。#28 使用不受支持的 ROS domain 233，深度话题未出现，不计功能测试。
- 追加诊断：#30 先生成匹配 B-spline/READY，随后 action 以 `pose_stale` 安全终止，未完成 SIGINT 关闭验收。独立 adapted-odometry observer 最大 gap 229 ms；导航 Python 主线程采样在 callback gap 内约105–115% CPU，样本期平均约76%。UST start 成功但只有 metadata、没有事件流，因此无法读取 RMW take/callback 时间。进程线程取样和 trace 会增加少量运行负载。
- 结论：导航进程主线程高 CPU 与明显 callback gap 同现；上游 status history 也有约1秒长尾，且 trace 未提供有效事件流。根因尚未区分 executor 轮转、Python 回调工作、定位状态生产或 RMW 交付。`Destroyable` teardown 异常仍待定位。
- 下一步：获取导航主线程 Python stack/profile 并修复 UST 数据落盘，再关联独立状态/里程计接收、navigation RMW take 与 callback 时间。EGO 0.4秒 timeout 保持 PROVISIONAL；在输入与 teardown 可重复前不进入 PX4 trajectory following。
- 证据：`progress/evidence/p4-navigation-shutdown.json`；构建与合成日志位于 `artifacts/runs/p4-navigation-live-ego-20261017-25`；live runs #22、#24、#26–#30 位于对应 artifacts 目录。
