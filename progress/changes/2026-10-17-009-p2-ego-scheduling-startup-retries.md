# P2 EGO 调度诊断重试与定位启动失败

日期：2026-10-17。对话摘要：[2026-10-17-009-p2-ego-scheduling-startup-retries.md](../../collaboration/dialogues/2026-10-17-009-p2-ego-scheduling-startup-retries.md)。

- 修改：将 run #26 的无有效定位结果加入 P2 输入间隔报告；同步更新 CURRENT 并写此记录。
- 运行：使用 EGO diagnostic overlay #04，probe 40.026 s；深度 READY，localization 在11.182墙钟秒后 `initialization_timeout`，优化里程计、EGO 深度／位姿、配对输入和占据点均为0。VINS raw 日志报告 `Initialization finish!` 并持续给出 solver 行，但 adapter 没有接纳到有效匹配输出；具体差异尚待定位。
- 排除：run #26 不能验证 EGO callback/timer 诊断。独立运行进程清理后没有活跃 Gazebo、VINS、EGO 或 probe 节点。
- 下一步：对比 run #23 与 #25/#26 的 VINS telemetry、raw topic publisher identity、source stamps、adapter health gates；待 TRACKING 重现后再运行 EGO steady-clock 测试。

- 后续排查修正：run #25–#28 的复测脚本在复制时没有更新 `VINS_NS` 取值路径，实际读取 run #24 manifest，使 VINS 输出到旧 epoch namespace。此前将 `initialization_timeout` 解释为定位启动不稳定的判断撤回；详情见[namespace 修正记录](2026-10-17-010-p2-vins-session-namespace-fix.md)。
