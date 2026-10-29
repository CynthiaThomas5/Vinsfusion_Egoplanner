# #314 对话摘要：分离低位 rear scan 的 yaw/pitch 动作

- 目标：按用户指示继续完成 N08；单程目标到点停止，返航仍是独立命令。
- #313 结果：低位回收完成，低位后向旋转并同时 pitch-up 时 normalized_cost=1.022129 越过原门限；没有释放后准入或飞行。
- 决策：保持低位 rear view 和先下降次序，将 pitch-only 上仰与 yaw-only 转向拆分；回中后单独复位 pitch，原阈值不变。
- 静态验证：profile 19阶段，45项测试、结构检查、JSON/Shell/关节限位/diff 检查均通过。
- 下一步：冷启动 #314；只有完整 N05、preflight、前向几何门通过才允许单程 motion-cancel goal。拒绝时不发 goal/enable，读回后安全停止。
