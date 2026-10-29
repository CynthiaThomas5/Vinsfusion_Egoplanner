# #405 N10.3 depth fault terminal calibration

- 用户授权继续完成 N10.1–N10.7 范围内的剩余测试和交付；N15 正式十二次故障测试、N16 正式十分钟任务仍在 N10 冻结后。
- 一次 emergency disarm 授权已在 #391 使用；#405 不使用紧急 disarm。
- 不恢复项目自加残差、经验速度、连续健康等待或 raw-known-free 全包络门；离线指标与采集器不改变 flight control decision。EGO、PX4 原生策略继续有效。
- #404 的共享 parameter_bridge 承载多个传感器，不能将其进程退出解释为 depth-only 故障。已使用 N03 的隔离 depth bridge 路由和显式 source-stamp fault relay，左右双目与 IMU 保持直通。
- 首次运行自然 fault landing 成功，但 relay 在 SIGINT 收尾时没有写出注入计数，因此保留为 evidence-incomplete；修复报告检查点和 evaluator 日志源后，在新 run `n10-20261028-405-depth-timeout-terminal-r02` 完成同协议校准。
- r02：3.0 sim s depth 丢帧窗口；91 帧丢弃，窗口前/后转发 1,138/536 帧。窗口内 left/right/IMU 收据 90/91/749。EGO `depth_odom_timeout` 使 action abort；bridge 因相同故障自然进入 LANDING 并到 LANDED/disarmed。15 s 独立终态读回、零后续控制通过；没有 operator-disable/emergency disarm。窗口到 landing 的 0.608 sim s 仅记录为描述量。
- 离线判断器首次误读 planner observer log，已改为使用 native ROS launch `vio.log` 并补回归；不改变 flight record。最终 10/10 checks PASS。资源、sensor capture、runtime identity 和报告哈希见校准证据。
- 当前仅关闭 depth-loss 单类一次校准，不是 N15 正式次数，也不代表 N10 完成。下一项离线复核 #404 map classification、tracking-clearance 和 resource capacity，然后校准其他仍缺当前版本依据的故障类别；验收依据、干净重建、回归和 N10.7 freeze 继续保留未完成状态。
