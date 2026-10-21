# P4 clock jump callback 与 live 调度复测

- 日期与任务 ID：2026-10-17-025。
- 用户目标与约束：继续完成 `GOAL.md`，本轮沿 P4 callback-gap 诊断；只推进单 D435i 仿真，不启动 PX4 控制，不放宽 freshness guard。现有工作树内容视为用户已有修改，不回滚、不暂存、不提交。
- 已确认的决定：#31 Python 全线程栈显示旧版导航节点为 `/clock` 额外维护逐消息订阅；以 rclpy `Clock.create_jump_callback` 监视至少 1 ns 负向跳变，保留 `clock_regression` 的取消和清轨迹语义。合成测试须用单调前进时钟恢复，不能把第二次回退误当恢复。
- 实施范围：更新 `uav_navigation.node`、adapter 测试、导航组件配置及契约说明；以独立目录构建 #32；扩展 live 复测至 #42，保留各次环境及 harness 排除记录，并整理当前 shutdown 证据。
- 证据与判断：#32 单包构建和合成 action 测试通过。#33 生成匹配 B-spline/READY，之后因 `localization_status_stale` 先 ABORT；回调 gap 约0.50秒，主线程采样58.3%，不能归结为单一代码路径。#34 因容器 `/dev/shm` 满排除；清理无占用临时段后，#35 仍有 IMU receipt gap、EGO 深度/位姿配对超时和定位 stale。#36 使用错误基础镜像；#37 包装器误判 setsid 子进程已退出而未发信号；#38 freshness 先决条件未满足；#39 ROS domain 超 Fast DDS 范围；#40 轮询延迟晚于 READY 后约98 ms 的 stale ABORT；#41 harness patch 断言在启动前失败，均不作行为结论。#42 使用正确派生镜像和512 MiB `/dev/shm`，probe 在匹配 READY 后直接向导航节点 PID 发 SIGINT，action 与 traj_server 对同 goal/epoch 返回 `navigation_node_shutdown` ABORT，无后续 READY，进程退出码0。当前 build #32 有一次 live shutdown 通过，但仍有1.7–2.1秒 callback gaps、四次短采样 CPU 100%、IMU 收包 gap 最大1.141秒和两个异步 Destroyable 异常；调度根因与干净 teardown 未证明。
- 待办：先用更长的无目标运行按统一 wall/ROS 时间关联相机、VINS、adapter、导航和 EGO 输入，区分发布、DDS 收包与 executor 回调长尾；稳定后再复测 caller-cancel、活动目标 SIGINT 与 teardown。P4 与 GOAL 均保持未完成。
- 对应改动记录：[progress/changes/2026-10-17-025-p4-navigation-clock-jump-callback.md](../../progress/changes/2026-10-17-025-p4-navigation-clock-jump-callback.md)。
