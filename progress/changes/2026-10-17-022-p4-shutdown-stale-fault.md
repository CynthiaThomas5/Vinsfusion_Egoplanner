# P4 shutdown ABORT 与 live stale 故障路径

- 任务 ID／日期：022／2026-10-17
- 对话摘要：[2026-10-17-022](../../collaboration/dialogues/2026-10-17-022-p4-shutdown-stale-fault.md)
- 修改文件：`uav_navigation/node.py`、`task_state.py`、导航状态／action 测试、`probe_mapping_runtime.py`、新增 `probe_localization_freshness.py`；更新导航包说明、接口契约、README、CURRENT、milestones 和 goal checklist；新增 [P4 证据报告](../evidence/p4-navigation-shutdown.json)。
- 行为变化及原因：收到 SIGINT/shutdown 时将活动任务 ABORTED 并发出按 goal/epoch 匹配的轨迹 ABORT；等待 action 执行回调排空，并留出一秒让结果服务投递后再销毁 node/context。run #10 证明单纯停止 executor 会让客户端收不到终态结果；run #11 验证修复后的顺序。mapping/freshness probes 显式处理 SIGINT 并保存运行报告。
- 验证类型：构建、合成 ROS 集成、单测、动态仿真、结构。
- 命令与环境：Jazzy 固定镜像 `sha256:fbdf66eb12efdea888acdafeb501280fa108513ae6b7703fe2a699ba97989f8e`；隔离 build/install 目录运行 7 包 colcon 构建；最终导航包重建；`ROS_DOMAIN_ID=213 FASTDDS_BUILTIN_TRANSPORTS=UDPv4` 下运行导航状态、action adapter 与 `traj_server` 测试。
- 结果及证据位置：新目录7包构建、最终 `uav_navigation` 重建、10项状态单测、action route/cancel/stale epoch/clock rollback/shutdown ABORT/callback drain 与 C++ traj_server 测试通过。run #08 因 stale 输入提前 ABORT；#09 规划与 caller-cancel 通过；#10 暴露 action result 投递竞态；修复后 #11 活动目标 SIGINT 下 action 客户端收到 `navigation_node_shutdown` ABORT，traj_server 匹配清轨迹，无后续 READY，supervisor 退出码0。构建、测试、live 日志及 SHA-256 见报告。
- 未验证与 PROVISIONAL：0.4 s EGO timeout 仍是临时值，run #08 stale 根因未确定；#11 的独立 mapping 观测窗口出现 `depth_stale`，输入稳定性未证明。无轨迹跟踪、到达、PX4、SITL 控制或实机证据；P0–P6 和 GOAL A–H 均未通过。
- 下一步：诊断 propagated-stale 与配对地图输入节奏；重复 caller-cancel 和活动目标 live SIGINT 运行；链路稳定后再推进 PX4 bridge 和 SITL 轨迹跟随。
