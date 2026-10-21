# P4 正常时钟活动目标关闭诊断

对话摘要：[2026-10-17-029](../../collaboration/dialogues/2026-10-17-029-p4-normal-clock-active-shutdown.md)

本轮以正常 canonical `/clock` 复测活动目标 SIGINT，并为连续 freshness 等待加上逐项诊断。没有修改生产源码、配置、时钟速率或 EGO timeout；未启动控制器或 PX4。

#59 因导航节点记录约2.9秒 status/timer/optimized-odometry 回调空档，在 action goal 回调时按 0.5秒 freshness guard 拒绝目标，未进入规划或 SIGINT。#60 的1秒稳定窗在15秒内未成立，未发送目标；该运行未记录逐项门槛计数。#61 加入5秒 pipeline warm-up 与逐项门槛统计后，外部 status/odom/map/depth/pair 通过1秒稳定窗，等待共4.295秒，其中有1,782个采样检查未满足 pose/depth 配对 freshness，其余被测检查失败0次。

#61 目标 `381219f6c3ec4f338c91dbcf789fa018`、epoch `e86ba045d9a4483eb396044e894e40fc` 的 B-spline/READY 匹配，终端 yaw 为请求的0.7 rad，样条到首个 READY 相差9 ms。SIGINT 后 action 返回 `ABORTED/navigation_node_shutdown`，traj_server 对同 goal/epoch 发 ABORT，后续 READY 数为0；导航与 probe 退出码均为0。`/clock` 只有 canonical `d435i_bridge` 一个 publisher，`/clock_raw` 不存在，PX4 控制话题审计为空，node list 未含 controller/PX4。

#62 使用新 domain/partition 独立复测也通过：1.002秒稳定窗内所有外部 freshness 检查通过，B-spline 与 READY 时间戳一致，action 与 traj_server 收到匹配 ABORT，后续 READY 为0，两个进程退出码0。#62 导航仍记录3.79–3.82秒 callback gaps和两条异步 Destroyable 异常，EGO 有30条 `odom or depth lost!` 与10条 solver error；#61有43条输入丢失。两次关闭路径通过不代表输入稳定、轨迹跟踪或到达通过。四次运行及逐项日志写入 [P4 shutdown evidence](../evidence/p4-navigation-shutdown.json) 与各自 run manifest。

验证：`bash -n` 检查 #59–#62 wrapper；`python3 -m py_compile` 检查 #59–#62 run-private probe；容器 live wrapper #59/#60 返回7并保留前置失败，#61/#62 返回0且达到上述 ABORT 条件。静态结构与 manifest 哈希检查在文档更新后执行。

下一步在 canonical /clock 下对齐测量 pose/depth 配对输入与导航回调间隔，缩小外部 observer 连续与导航节点出现长 callback gap 的差异来源；在 freshness 与规划稳定前不开始轨迹跟踪／到达验收。
