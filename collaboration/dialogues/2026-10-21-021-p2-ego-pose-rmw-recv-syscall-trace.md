# GOAL C EGO receive syscall diagnostic #355

- **任务摘要**：在已确认的EGO UDP buffer配置下，追踪DataReader空history区间的participant socket receive syscall返回，区分host packet tap与进程socket receive。
- **用户约束**：仅做P0–P6单D435i仿真导航诊断；不改canonical源码、QoS、config或系统参数；不订阅truth／完整世界地图，不发布control。
- **决定**：复用#353/#354 run-local `listenSocketBufferSize=212992` profile及probe库。临时容器只安装strace，并在EGO launch上加 `-f -ttt -T`；receive调用设为raw参数，只记录FD和返回长度，不展开buffer内容。
- **结果**：FD70成功bind UDP62427，与TID808 `dds.udp.62427` 对应。全程104,439次FD70 `recvfrom`成功返回。最长take间隔仅0.392429 s（低于0.4 s门）；该短窗内96次wait为unread=0、一次ready/unread=1，FD70有308次成功`recvfrom`、0次错误。adapter publish与独立reader回执各只有1条；MapStatus从ready转到`map_reset_acknowledged`且map_id变化，localization后续`propagated_from_future`。planner probe在ready前超时，没有目标或轨迹。
- **结论边界**：strace引入时序开销且长gap未复现；短窗receive返回数据报可能来自participant其它topic，不能证明camera_pose进入reader history。该run不作为原长gap的根因证据。
- **下一步**：换用更低开销的receive-path计数，在MapStatus、epoch、map_id稳定且publisher／独立reader连续的窗口复测；随后继续vehicle-safe视角动作、多布局覆盖和轨迹执行。
- **证据**：[报告 #355](../../progress/evidence/p2-ego-pose-rmw-recv-syscall-trace-20261021-355.json)、[运行清单](../../artifacts/runs/p2-ego-pose-rmw-recv-syscall-trace-20261021-355/run-manifest.json)、[改动记录](../../progress/changes/2026-10-21-021-p2-ego-pose-rmw-recv-syscall-trace.md)。
