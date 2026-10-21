# P4 导航状态接收与 shutdown 诊断

- 任务 ID／日期：023／2026-10-17
- 对话摘要：[2026-10-17-023](../../collaboration/dialogues/2026-10-17-023-p4-navigation-status-diagnostics.md)
- 修改文件：`src/own/uav_navigation/uav_navigation/node.py`；更新 `README.md`、`progress/CURRENT.md`、`progress/evidence/README.md` 和 [P4 证据报告](../evidence/p4-navigation-shutdown.json)。运行配置、goal 门控阈值和控制发布路径未改。
- 行为变化及原因：goal callback 对 stopping、定位状态/epoch/新鲜度、优化里程计、EGO/轨迹取消订阅、target frame 和目标数值分别记录拒绝原因，拒绝条件保持原样。status stale 门控输出本地接收年龄、状态原因和 odometry 年龄；长状态回调间隙恢复及超过 freshness guard 的导航 timer 调度间隙也会写入日志，用于定位 #14 的静默拒绝及 #13/#16 stale 中止。
- 验证：固定 Jazzy 容器中运行隔离 `colcon --base-paths src/own --packages-select uav_navigation` 构建（run #19，1 package）；运行 `python3 tools/test_navigation_task_state.py`（10项通过）和 `python3 tools/test_navigation_adapter.py --project-root /workspace`（action route/cancel/旧 epoch 拒绝/clock regression/shutdown ABORT/callback drain 通过，旧 epoch 用例输出了具体 frame 拒绝日志）。构建及测试日志和 SHA-256 见 P4 证据报告。
- 动态证据：#12 未达到 TRACKING/map goal 前置条件；#13 在目标规划后以 `pose_stale` ABORT；#14 初始定位、地图和22.4 ms odometry 观察年龄均满足，但旧版日志无法区分拒绝门；#15 为探针文件路径错误，不计功能测试；#16 规划后以 `localization_status_stale` ABORT，独立观察器测得 IMU stamp 间隔5 ms、propagated stamp 最大间隔5 ms，不能代表导航 reader 到达。#18/#20 各自完成活动目标 SIGINT 的匹配 action ABORT、EGO 轨迹清除及干净进程退出；#18 记录1.673秒状态回调间隙并出现 map-stale EMERGENCY_STOP，#20 短活动窗口未观察到超过0.5秒的导航状态或 timer 间隙。#21 caller-cancel 通过：action 结果为 `caller_cancel`、traj_server 对同 goal/epoch 发 ABORT、ABORT 后 READY 数为0；同 run 的 status/timer 回调分别停顿2.582/2.581秒，提示节点回调调度受阻但未定位原因。详见 [P4 运行证据](../evidence/p4-navigation-shutdown.json) 和各自 `artifacts/runs/p4-navigation-live-ego-20261017-{12,13,14,15,16,18,20}`。
- 未验证与限制：状态 reader 投递与 executor 调度根因尚未区分；#20 的活动窗口较短，不证明长时输入稳定。EGO 0.4秒 timeout 仍为 PROVISIONAL；无轨迹跟踪、到达、PX4 控制、SITL 闭环或实机验收；P0–P6 与 GOAL A–H 均未通过。
- 下一步：在同一动态运行采集进程/thread CPU 使用、status callback 间隙、timer 间隔和 EGO pose/depth/map 更新；查清 #21 的调度长间隙后再评估是否调整 RMW/QoS、executor 或 stale guard。
