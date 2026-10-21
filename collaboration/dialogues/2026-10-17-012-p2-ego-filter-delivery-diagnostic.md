# P2 EGO filter 接收与交付诊断

日期：2026-10-17

- 用户约束：继续 GOAL.md P0–P6；本轮只诊断 P2 单 D435i 仿真输入；保护已有 staged／unstaged 修改；不启动 PX4 控制或实机飞行，不修改旧工程来源。
- run #34 使用 patch 0015 构建，但定位适配器在 2.921 s 锁定为 imu_stale，EGO 没有输入，排除运行结论。
- run #35 复制脚本时漏掉 launch_runner.py 和 sensor relay launch 文件，未启动仿真，记录为 harness 错误并排除。
- run #36 深度 READY、定位 TRACKING、raw VINS 输出正常，但 EGO 清图服务的客户端未收到响应；mapping adapter 输入门保持关闭。run #37 将 EGO 服务启动并确认可见后再启动 mapping adapter，服务 reset 收到确认。
- run #37 有效观测60.026 s：深度 READY、定位 TRACKING、496组 EGO depth/pose 配对、地图峰值1905。probe 源 stamp 最大配对间隔0.297 s；EGO timeout 在窗口后段出现46条。期间 EGO 内 filter pose 接收数停在514，depth 接收数由522升至541；两类 RMW message-lost 计数均为0。独立 observer 在同一窗口继续收到 pose，最高 stamp45.508 s。之后另有6条窗口外 timeout。
- 静态检查：EGO 入口调用 rclcpp::spin(node)，过滤器与 GridMap timers 未指定独立 callback group；depthPoseCallback、occupancy timer 和 reset 访问共享、未加锁的地图状态。直接换多线程执行器会引入数据竞争风险。#37 的 callback/timer/fusion耗时没有显示已测出的占用 timer 过载。
- 决定：patch 0015 收窄出 EGO 内 pose filter 回调没有收到／交付消息这一范围，RMW message-lost 无事件；根因仍可能涉及 executor 调度、reader 队列或其他交付路径，尚未确认，也没有修复。0.4 s timeout 与 ground_height=-0.15 m 继续为 PROVISIONAL。
- 产物与 SHA256、run 排除原因、build #07 状态更新在 [P2 interval evidence](../../progress/evidence/p2-ego-input-interval-diagnostic.json) 和 [P0 diagnostic build evidence](../../progress/evidence/p0-ego-map-timeout-diagnostic-build.json)。无目标、控制器、PX4 或 actuator。
