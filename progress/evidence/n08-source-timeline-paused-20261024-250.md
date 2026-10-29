# N08.2am #250：用户暂停后的安全收尾

## 任务和中断点

#250 原计划用既有 negative-only 支架 profile 和只读 localization source timeline 区分 raw VINS 时间戳超前与 adapter `/clock` 回调滞后。用户暂停 Goal 时，支架扫描完成 3/16 阶段，尚未到 prescan-ready、N05 after/post-release gate 或 mission current-area gate。

部分时间线已保存，包含 `/clock`、raw/adapter propagated、raw/adapter optimized、telemetry、LocalizationStatus、MapStatus 与 bridge detail；它因支架扫描提前结束，不能回答 #249 的时间戳来源，也不构成 N05／N08 通过证据。

## 安全收尾

扫描器收到 SIGINT 后 ROS context 先关闭，内置 fixture cleanup 未完成。仿真容器因此保持运行；没有强停。随后运行安全恢复程序，以 20 仿真秒平滑将支架关节回到地面初位，再脱离并移除 fixture。Gazebo 独立 model list 确认 fixture 不存在；恢复记录确认最终 PX4 DISARMED、landed。5 秒独立桥接器读回再次确认 DISARMED、landed、bridge DISABLED、控制样本为零。`tools/project.sh stop` 返回 0，容器 Exited(0)。

## 任务状态

没有完成当前地图门，没有 compute-only 曲线证书、XY 或制动测量；N08 仍 `in_progress`，Goal 状态为用户暂停。N07 已通过项目不复测。

恢复时先审阅 #250 部分时间线和 #249 锁存快照；若证据仍不能区分 raw propagated 与 `/clock` 收件时序，再用有可安全收尾处理的诊断运行。不得放宽 20 ms 门或其他准入阈值。

## 产物

运行数据和恢复脚本在 `artifacts/runs/n08-20261024-250-negative-only-clock-timeline/`；相对路径与 SHA-256 见本报告旁的 JSON。
