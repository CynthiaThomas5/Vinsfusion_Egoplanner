# N08 #324 普通单目标 terminal-stop 第二次冷启动通过

对话摘要：[2026-10-26-324](../../collaboration/dialogues/2026-10-26-324-n08-terminal-stop-pass.md)。验收报告：[Markdown](../evidence/n08-terminal-stop-20261026-324.md)、[JSON](../evidence/n08-terminal-stop-20261026-324.json)。

- #324 与 #321/#322 runtime-contract、目标／planner配置和镜像身份一致。新 PX4/VINS/map会话下完成N05支架扫描、fixture释放、同身份post-release与current-area online/offline准入、preflight及普通单目标。
- native action succeeded，独立 evaluator全部 checks通过；实际位移0.59902m，峰值向量速度0.08282m/s，末端制动路径0.28868m，持续减速响应0.816s，最大独立跟踪误差0.08379m，3秒hold通过。无返航goal。
- 前向全机capsule 25/25 free，目标两端hold及降落候选通过。末态独立读回LANDED/disarmed/control disabled、控制计数0，容器exit0。
- fixture helper最终cleanup的stale警告和mission绘图依赖缺失均保留；显式fresh post-release N05及无绘图独立评估通过。未改源码／阈值。
- 当前普通到达资格2/3；下一项#325相同冻结身份第三个独立cold-start terminal_stop。
