# 修改与验证记录

- 任务 ID／日期：031 / 2026-10-17。
- 对话摘要：[P4 导航 executor 状态锁诊断](../../collaboration/dialogues/2026-10-17-031-p4-navigation-executor-lock-trace.md)。
- 修改文件：`src/own/uav_navigation/uav_navigation/node.py`、`tools/test_navigation_adapter.py`、`progress/evidence/p4-navigation-shutdown.json`、`progress/CURRENT.md`、`progress/evidence/README.md`、`README.md`，以及 #67–#76 的 ignored run manifests。
- 行为变化及原因：#75 直接测得一次 odometry 恢复告警调用耗时3.518167秒，包含它的状态锁持有3.518342秒；独立 observer 在该窗口仍收到 status 和 optimized odometry，最大间隔52.417/112.796 ms。#73 的同类 odometry 锁持有为4.011秒。#69 的 accepted-goal INFO 行与1.878秒 `_execute_goal_impl` 锁释放时间只差约10微秒，属于强相关、未单独计时。现将共享状态锁内的目标拒绝／接受、定位／里程计／clock／timer 日志移到状态和任务事件处理完成、锁释放之后；日志条件与内容保留，导航状态和任务事件仍按原先顺序在锁内更新。
- 验证类型：静态／编译／合成 ROS 集成；另有修复前 live 诊断。没有完成修复后 live、SITL 飞行或实机验证。
- 命令与环境：在 `d435i-vins:dev` 固定 Jazzy 容器的新 build/install 目录构建 `uav_navigation`（1/1）；`python3 tools/test_navigation_task_state.py`（10/10）；`ROS_DOMAIN_ID=228 python3 tools/test_navigation_adapter.py --project-root /workspace`（通过目标路由、取消、旧 epoch 拒绝、clock 回退、冻结时钟 stale、shutdown ABORT，并分别阻塞 odometry warning 与 accepted-goal INFO 验证另一线程仍可取得状态锁）。运行命令、输出与哈希见 [#77 run manifest](../../artifacts/runs/p4-navigation-lock-log-outside-20261017-77/run-inputs.json)。
- 结果及证据位置：#73/#75 的导航 trace 与独立时间线已写入 [P4 shutdown 证据](../evidence/p4-navigation-shutdown.json)，#67–#76 每个 live run 的输入和输出均有 `run-inputs.json`。#75 活动目标 shutdown 路径通过，但为修复前版本；#76 只运行了最初将 odometry 告警移出锁的构建，且在 goal 前停于 `telemetry_stale`、地图为空。最终完整锁外日志版本只有 #77 构建和合成回归证据。
- 未验证与 PROVISIONAL：同步 logger/output 路径为什么会阻塞尚未知。#69 的 accepted-goal logger 仅由时间相关性提示，未做单独边界计时。`_process_events` 与发布仍在共享锁内；当前修复没有排除其他非日志操作造成的锁停顿。#67 是导航本地输入可见性症状；#70 的高量 instrumentation 排除；#74 没有加载完整 run-private Python 包；#76 无活动目标。十次正常时钟活动目标 shutdown 路径观察不代表导航稳定性或 P4 通过。
- 下一步：用最终 #77 构建重新跑 canonical `/clock` 活动目标并先启动独立 observer；检查回调间隔和状态锁 hold，观察匹配 B-spline/READY 与 SIGINT ABORT。若 live 输入稳定，再做轨迹跟踪／到达、地图故障响应、多场景地图／快照、10分钟负载及剩余 P0–P6 / A–H 验收。

代码提交：无。最终源文件 SHA-256 记录在 `progress/evidence/p4-navigation-shutdown.json`。
