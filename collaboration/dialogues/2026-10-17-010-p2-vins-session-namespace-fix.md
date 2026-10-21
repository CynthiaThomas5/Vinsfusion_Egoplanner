# P2 复测脚本 epoch namespace 修正

日期：2026-10-17

- 用户约束：继续 GOAL.md P0–P6；保护已有 staged／unstaged 文件；不推送；不启动 PX4 控制或实机飞行。
- 根因：run #25–#28 的复制脚本只替换了第一次 run 路径。`VINS_NS` 的 Python 读取仍指向 `artifacts/runs/p2-ego-map-healthy-input-20261017-24/session/session.json`，而 adapter/probe 使用各自新 session 的 epoch。
- 证据：run #28 raw graph 看到了 namespace `/vins_raw/s_183aa722ef62497c918daf71b53d2ed1` 下的 VINS node，但 run #28 adapter session 是 `96633582d01243088fcedb036b8271f9`，此 namespace 的 publisher endpoint 数为0。probe 输出、VINS solver log 和命令行配置保持；该 mismatch 足以解释 adapter `initialization_timeout` 和 EGO 输入数为0。
- 修正：run #29 的脚本从 `$RUN/session/session.json` 动态读取 `VINS_NS`，并保存 raw VINS node/topic/publisher 图以及 EGO callback/timer steady-clock 指标。
- 决定：#25–#28 全部改记为 harness namespace 错误，不作为 VINS 启动不稳定或 EGO 时序证据。
- 待决：run #29 尚在执行；确认 VINS 发布落在当前 epoch，随后分析 EGO 诊断。

- 后续结果（详见对话摘要011）：run #29 的当前 epoch raw VINS 节点与三个 publisher endpoint 均正确，但健康窗口仍有 EGO timeout；run #32/#33 测到 EGO pose 接收计数停顿，不能归因于先前的 namespace 错误。
