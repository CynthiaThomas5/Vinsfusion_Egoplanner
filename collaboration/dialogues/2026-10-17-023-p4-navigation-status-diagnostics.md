# P4 导航状态接收与 shutdown 诊断

- 任务：继续排查 P4 动态 D435i/VINS/EGO 目标规划与活动目标关闭的 stale/拒绝问题。
- 用户约束：按项目 `AGENTS.md` 工作；只推进单 D435i 仿真导航，不启动实机飞行；真值、地图、控制仍按各自隔离边界执行；旧实验区只读；不把结构或构建通过写成系统验收。
- 决策：保持 goal 接受条件与 freshness 阈值不变。导航拒绝目标时记录具体门控原因；状态过期和回调恢复时记录本地接收年龄；timer 间隔超过状态 freshness guard 时记录调度间隙。
- 观察：导航包诊断版在 Jazzy 隔离构建及 action 合成测试通过。#13 因 `pose_stale` 终止；#14 目标拒绝无旧版诊断；#15 因 wrapper 探针路径拼写错误未测试目标；#16 因 `localization_status_stale` 终止，而单独 freshness probe 看到连续 IMU/propagated 输入。修正后 #18/#20 两次活动目标 SIGINT 均完成匹配 ABORT、traj_server 清轨迹、进程退出码0；#21 caller-cancel 也通过，action 返回 `caller_cancel`、ABORT 后 READY 数为0。#18 记录导航状态回调空档1.673秒并观察到 EGO map-stale EMERGENCY_STOP；#21 status 与 timer 回调同时停顿约2.58秒，提示节点回调调度受阻；#20 短活动窗口未触发0.5秒状态/timer gap 日志。
- 待决：节点 status/timer 同步回调间隙的 CPU、executor 或 RMW 根因；在动态负载下重复 caller-cancel 与活动目标 shutdown；mapper/EGO 输入间歇、规划稳定性与轨迹跟踪。
- 后续：在最终诊断版同时采集进程/thread CPU 与状态/timer 回调间隔，再重复 caller-cancel；对齐观察后再决定是否修改 QoS、executor 或超时。0.4秒 EGO timeout 保持 PROVISIONAL。在输入与取消路径稳定前不推进 PX4 trajectory following。
- 证据：`progress/evidence/p4-navigation-shutdown.json`；原始运行位于 `artifacts/runs/p4-navigation-live-ego-20261017-12` 至 `-20`。
