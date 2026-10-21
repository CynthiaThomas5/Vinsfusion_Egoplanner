# P4 shutdown ABORT 与 live stale 故障路径

日期：2026-10-17。

## 任务摘要

继续 P4 action lifecycle 修复和动态 D435i/VINS/EGO 验证，记录 run #08 stale 故障、run #09 caller-cancel、run #10 暴露的结果投递竞态，以及修复后 run #11 活动目标 SIGINT 关闭。

## 用户约束

- 仅推进单 D435i 仿真导航 P0–P6；旧工程与 ROS_SEARCH 实验区只读，已有工作树修改不回滚、不混入提交。
- PX4 控制设定点和 `OffboardControlMode` 仍只能由 `uav_px4_bridge` 发布；本次不启动 PX4 或控制器。
- 区分构建、合成测试和 live 仿真证据；失败结果不得当成阶段通过。

## 决定与证据

- 节点关闭时对活动目标使用 ABORT，并按 `goal_id + epoch` 清理轨迹；等待活动 action callback 完成，并给 action result service 一秒投递窗口后再销毁 node/context。
- `uav_navigation` 和 mapping/freshness probes 显式处理 SIGINT，保存必要运行报告后完成 executor teardown。
- 最终源码 Jazzy 新 build/install 目录 7 包构建及最终 `uav_navigation` 重建通过；10 项任务状态测试、action shutdown ABORT/callback drain 和 C++ `traj_server` 合成测试通过。
- live run #08 生成匹配 B-spline，但 EGO 最后一次占据更新在仿真4.373 s；4.789 s stale 检查时输入年龄416 ms，超过0.4 s临时 timeout。EGO 进入 EMERGENCY_STOP，action 以 `localization_propagated_stale` ABORT，而非 caller-cancel。根因未定。
- run #09 再次通过目标规划与 caller-cancel；run #10 中 supervisor 已发布匹配轨迹 ABORT 并正常退出，但客户端未收到结果，确认是 teardown 时机竞态。修复 callback drain 和 result 投递窗口后，run #11 活动目标 SIGINT 验证通过：客户端收到 `navigation_node_shutdown` ABORT，traj_server 清理同 goal/epoch 轨迹且无后续 READY，进程退出码0。
- run #11 独立 freshness probe 约20秒内未观察到 propagated-stale，传播源龄 P95/最大为1/6 ms；mapping probe 有111组配对输出，但观测窗口出现 `depth_stale`，不证明输入稳定。无轨迹跟踪、PX4 或飞行验收。

## 待办

- 追踪 run #08 的 propagated odometry、mapping gate 与 DDS/executor 输入节奏，确定 stale 来源；0.4 s timeout 维持 PROVISIONAL。
- 重复 run #11 活动目标 SIGINT 和 run #09 caller-cancel，确认关闭及规划链路可重复。
- 输入稳定后再开始 PX4 bridge/SITL 轨迹跟随，保留唯一控制发布者约束。
