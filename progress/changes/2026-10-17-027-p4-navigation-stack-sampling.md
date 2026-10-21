# P4 正常时钟栈采样与执行器热点诊断

- 任务 ID／日期：2026-10-17-027。
- 对话摘要：[2026-10-17-027-p4-navigation-stack-sampling.md](../../collaboration/dialogues/2026-10-17-027-p4-navigation-stack-sampling.md)。
- 修改文件：#57 run-private wrapper、采样输出与 `run-inputs.json`；`progress/evidence/p4-navigation-shutdown.json`、`progress/evidence/README.md`、`progress/CURRENT.md`、`README.md`、本记录和对话摘要。没有生产源码或正式参数变化，P4 仍为 `in_progress`。
- 运行结果：在与 #56 相同的正常 `/clock`、无目标仿真组合下，外部采样器在4秒后发送80次 SIGUSR1 faulthandler 栈采样，间隔约0.22秒；同时以120 ms窗口测量 `/proc` 线程 CPU。导航保持存活并正常清理。22个执行器窗口覆盖44.147秒，generator 主线程 CPU中位数0.668 s/s。80个瞬时主线程栈中，`rclpy/executors.py:781`（`WaitSet.wait`）出现26次，`:803`（waitable readiness）出现9次，`:749`（waitable entity count）出现8次。它们是栈位置频率，不是 CPU 时间分摊或根因证明。
- 状态与边界：状态探针850个样本中832个有效；18个 `waiting_for_propagated` 样本都出现在启动期，随后持续收到有效 tracking 状态。EGO仍记录47条 odom/depth timeout。导航 stale warning 在上游 teardown 后出现。未发送 action goal；无 controller、PX4 bridge、PX4 或控制输出。
- 验证：80/80栈信号发送成功；instrumentation synthetic preflight 通过；wrapper 退出码0，导航在观察结束时存活；后续结构检查、哈希校验和 diff 检查见本轮最终结果。原始计数、栈文件、系统日志和状态输出均由 run manifest 以 SHA-256 关联。
- 局限与下一步：采样和 observer 会给进程增加少量开销，瞬时栈不能确定热点 CPU 占比。#56 的 WaitSet 系统采样同样不能解释 generator CPU；EGO timeout仍未解决。下一步在正常时钟下复测 caller-cancel 与活动目标 SIGINT，核对 freshness、轨迹响应和清理行为；不据此更改时钟、freshness guard 或 EGO timeout。跟踪／到达、地图故障响应、多场景地图、10分钟负载及其余 GOAL 要求仍待完成。
