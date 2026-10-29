# N08 #321 caller-cancel 停止链与进度交接

对话摘要：[2026-10-26-321](../../collaboration/dialogues/2026-10-26-321-n08-cancel-stop-pass.md)。运行证据：[报告](../evidence/n08-cancel-stop-measurement-20261026-321.md)、[JSON](../evidence/n08-cancel-stop-measurement-20261026-321.json)。

- 使用同一 N08 低速目标、当前 full-body 前向门和新冷启动完成 one-way single_goal motion_cancel。取消在 PX4 水平速度 0.04014 m/s、EGO 参考速度 0.05848 m/s 时触发。
- 当前版本的替代停止 spline、旧轨迹不恢复、实际停止／保持、终点降落候选与 landed/disarmed 均通过；取消至停车 0.30407 m，候选走廊 0.50 m。return_action_sent=false。
- native flight 与独立 braking evaluator 均 PASS。mission wrapper 仅因缺少可选 matplotlib 绘图依赖返回 1；保留该问题，并通过不绘图 evaluator 单独复核通过。runtime contract hash 为 75aaa541...，未改运行源码。
- 复用 #212 hold 基线和 #257/#260 同 runtime-contract compute-only／execute 受控对照；#321 补当前运行器取消交接及实际停车链。有限减速度观测不升级为安全下界。
- #321 不计入普通 terminal_stop 三次。下一步 #322 用相同冻结版本、N05 translation-only 支撑扫描和同一目标配置启动首个独立 cold-start single_goal terminal_stop。所有速度、健康、时钟、raw-map、空间及跟踪门保持不变；成功则继续 #323/#324，不重测 N07。
