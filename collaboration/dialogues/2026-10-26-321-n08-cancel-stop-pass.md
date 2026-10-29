# N08 #321 caller-cancel 停止与保持

- 用户范围：按 N08 完成计划持续完成目标；不复测已通过 N07。普通单目标到达即结束；返航如需进行必须是独立的第二段命令。
- 本次结果：fresh N05 扫描／释放准入、preflight、前向 full-body 走廊和终点候选通过；one-way motion_cancel native result 和独立评估均通过。取消触发、替代停止 spline、停车／保持、终点落地及安全读回均有原始记录。
- 关键值：取消水平速度 0.04014 m/s，取消至实际停车 0.30407 m，候选走廊 0.50 m；无人机最终 bridge LANDED、PX4 disarmed/landed、control disabled。
- 运行身份：runtime contract 内部 hash 75aaa541f7684b38fe0805b958e029fa21f8c6dd6ab00d2ebe1fae92c7e8a772；目标与 planner 配置 hash 记录于证据 JSON。
- 局限：本轮是 motion_cancel，不是普通 terminal_stop，不能计入普通目标三次。mission wrapper 的可选 --plot 缺 matplotlib 返回 1；同一运行不带绘图的独立 evaluator passed=true。
- 决定：复用 #212 与 #257/#260 三模式历史对照；#321 补实测取消链。下一项 #322 执行相同冻结版本的一次普通 single_goal terminal_stop。N08 父状态保持 in_progress。
