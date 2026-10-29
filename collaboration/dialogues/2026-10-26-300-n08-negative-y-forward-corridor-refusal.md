# N08 #300 负 Y 侧向缺图

- 授权范围：按计划完成 N08；普通目标到达后停止，返航为独立命令。
- #300 试验变量：N05 支架观测 profile 从 translation-only 改为现有 `n08_overhead_free_sector_view`；其余布局与阈值不变。
- 结果：15/15 阶段、夹具已删除；fixture helper 报 localization status warning，但身份连续、final localization valid，run summary diagnostic pass。post-release 与 mission current-area N05 online/offline 均通过；read-only preflight 40.002s 通过。
- N08 在 goal/enable 前因 forward corridor 与 start/terminal hold raw unknown 拒绝：首个 query 66 unknown，start/terminal 各 58；未知格位于 map ODOM y=−1.05m 薄层。未发布 goal/control，PX4 未解锁且 landed、bridge DISABLED，独立 control output 0，项目容器 exit0。
- 下一步 #301：使用既有 `n08_overhead_negative_side_view` yaw−π/2 侧向观察，唯一变量为观察 profile；fresh N08 corridor gate 通过前不启动任务。
