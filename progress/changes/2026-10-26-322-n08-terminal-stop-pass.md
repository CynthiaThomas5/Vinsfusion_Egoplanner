# N08 #322 首个普通单目标 terminal-stop 冷启动通过

对话摘要：[2026-10-26-322](../../collaboration/dialogues/2026-10-26-322-n08-terminal-stop-pass.md)。验收报告：[Markdown](../evidence/n08-terminal-stop-20261026-322.md)、[JSON](../evidence/n08-terminal-stop-20261026-322.json)。

- #322 使用与 #321 一致的 runtime-contract、goal profile、planner profile、模型和运行构建身份，完成完整 fresh N05 scan/release、mission preflight、current-area admission 与 native 单程目标。
- 正常 EGO goal 成功，独立评估所有 checks 通过；实际位移 0.59726 m、制动路径 0.28106 m、peak vector speed 0.07550 m/s、最大独立跟踪误差 0.08008 m、减速响应 1.504 s、3 s hold通过。未发送返航 action。
- 25 个 full-body 前向查询和起终点 hold、终点候选落地几何均通过；最后 landed/disarmed 独立读回通过且控制样本0，容器exit 0。
- N05 fixture helper 收尾短暂记录 localization receipt stale；夹具移除及 landed 后显式 same-identity online/offline post-release gate 通过。原警告保留。
- 外层 mission 因可选绘图库缺失返回1，但 native flight与无绘图独立 evaluator均通过；未改源码／配置。父N08仍in_progress，该 run 计普通目标三次中的1次。
- 下一项 #323：相同冻结身份再完成一次独立 cold-start single_goal terminal_stop。
