# P4 导航回调空档与稳态 watchdog 诊断

- 任务 ID／日期：024／2026-10-17
- 对话摘要：[2026-10-17-024](../../collaboration/dialogues/2026-10-17-024-p4-navigation-callback-overrun.md)
- 修改文件：`src/own/uav_navigation/uav_navigation/node.py`、`tools/test_navigation_adapter.py`、`tools/probe_localization_freshness.py`；更新 `README.md`、`progress/CURRENT.md`、`progress/evidence/README.md` 与 [P4 证据报告](../evidence/p4-navigation-shutdown.json)。
- 行为变化：导航 stale watchdog 显式使用 `ClockType.STEADY_TIME`，使其与 `time.monotonic()` 接收年龄匹配；原 status/odometry 门控、0.5/0.3秒阈值和控制边界保持不变。合成测试验证 ROS `/clock` 停住时墙上时间 watchdog 仍触发。Freshness probe 记录绝对墙钟时间并独立订阅 adapted optimized odometry。
- 构建／回放验证：固定 Jazzy 容器隔离构建 #25（1 package）通过；`python3 tools/test_navigation_task_state.py` 10项通过；`python3 tools/test_navigation_adapter.py --project-root /workspace` 通过目标路由、取消、旧 epoch、clock regression、冻结 `/clock` stale guard、shutdown ABORT。日志和 SHA-256 在 P4 证据报告。
- live 证据：caller-cancel #22/#26/#27 成功，活动目标 SIGINT #29 成功；#29 的导航 status/timer/optimized-odometry callback gap 为3.258/3.242/3.316秒，独立 adapted-odometry observer 最大189 ms，status history 最大约1.30秒；shutdown action 和轨迹 ABORT 匹配、进程 exit0，但出现 Destroyable 异常。#24 与 #30 分别在规划后由 `localization_status_stale` 和 `pose_stale` 安全中止。#30 导航主线程样本约105–115% CPU，但 trace 仅有 metadata，无 UST 事件流。#28 domain233 为无目标测试的前置条件失败。
- 局限：source status 自身可见约1秒收包长尾；线程 CPU 样本没有 Python 堆栈，且诊断采样可能增加负载。不能据此确定 executor、回调代码、状态发布或 RMW 的根因。重复 `Destroyable` teardown 异常尚未解释。没有轨迹跟踪、到达、PX4 控制或 P4/P0–P6 验收。
- 下一步：对 navigation Python 主线程做栈采样，修复 UST 事件采集，并和独立观测器、RMW take 与 callback 时间对齐；输入和 teardown 稳定前不推进 PX4 trajectory following。
