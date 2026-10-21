# P4 clock jump callback 与 live 调度复测

- 任务 ID／日期：2026-10-17-025。
- 对话摘要：[2026-10-17-025-p4-navigation-clock-jump-callback.md](../../collaboration/dialogues/2026-10-17-025-p4-navigation-clock-jump-callback.md)。
- 修改文件：`src/own/uav_navigation/uav_navigation/node.py`、`tools/test_navigation_adapter.py`、`config/components/navigation/task_supervisor.json`、`src/own/uav_navigation/README.md`、`docs/contracts.md`、`README.md`、`progress/CURRENT.md`、`progress/evidence/README.md`、`progress/evidence/p4-navigation-shutdown.json`、本对话摘要及本改动记录；补全 run #32 输入哈希并记录 #34–#41 排除报告。
- 行为变化及原因：移除导航节点对 `/clock` 每条消息的重复订阅回调，改用 rclpy clock jump callback 检测至少1 ns负向跳变；回调将 ROS clock 回退送入既有 core 锁定／任务 ABORT 路径。这样减少高频 callback 负担，同时保持故障语义。
- 验证类型：静态、编译、合成 ROS action、live 仿真诊断；未做 SITL 控制或实机。
- 命令与环境：Jazzy 隔离构建 `uav_navigation`（run #32）；`python3 tools/test_navigation_task_state.py`（10项）及 `python3 tools/test_navigation_adapter.py --project-root /workspace`；live runs #33–#42 使用不同 ROS domain 和 harness；#42 由 action probe 在 matching READY 后直接向导航节点 PID 发 SIGINT，运行于 `d435i-vins:dev` 与512 MiB `/dev/shm`。
- 结果及证据位置：#32 构建及合成测试通过，#42 当前 build #32 活动目标 SIGINT 得到 `navigation_node_shutdown` action ABORT、同 goal/epoch traj_server ABORT、ABORT 后零 READY、进程退出码0。#42 原始日志、probe、stack、freshness、wrapper 和输入哈希见 `progress/evidence/p4-navigation-shutdown.json` 及 `artifacts/runs/p4-navigation-live-ego-20261017-42`。#31 旧版 callback gaps 约3.9秒、四次 CPU 采样100%；#33 stale-abort；#35 出现 IMU 最大1.115秒 receipt gap 和 EGO 输入失配。#36–#41 由于基础镜像错误、包装器 PID 检查错误、freshness 前置条件、非法 domain、SIGINT 轮询延迟和 harness patch 失败而排除。
- 未验证与 PROVISIONAL：#42 虽为当前 build 一次 live shutdown 通过，仍有1.700/1.705/2.090秒 callback gaps、四次120 ms 主线程 CPU 100%采样、独立 IMU receipt gap 最大1.141秒和两个异步 Destroyable 异常；实时输入稳定、clean teardown、轨迹跟踪与到达未验收。发布、DDS 与 executor 根因未区分。定位 freshness 阈值及 EGO 0.4秒 timeout 保持 PROVISIONAL；没有放宽门限。
- 下一步：先运行更长的无目标 live baseline，在统一 wall/ROS 时间线上关联 D435i 深度/IMU、VINS 原始与传播输出、adapter、导航状态、EGO 配对与 map timer，定位长尾来源；输入稳定后重测 action 取消、活动目标 SIGINT 和 teardown。PX4 trajectory following 暂不启动。
