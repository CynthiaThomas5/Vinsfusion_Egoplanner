# P2 阶段出口审计与里程碑更新

- 用户目标：继续推进 `GOAL.md`，按阶段记录证据；不能将阶段通过扩写为整个项目完成。
- 用户约束：P0–P6 单 D435i 仿真范围；真值只允许进入 `debug_truth`；控制设定点与 Offboard 模式由 `uav_px4_bridge` 独占；保护已有 staged、unstaged、untracked 修改；不提交或推送。
- 审计范围：只检查 `GOAL.md` 阶段表中的 P2 条款——目标 Jazzy 构建、仿真初始化、受控平移与转弯、误差测量、失效门控。
- 决定：P2 阶段表条款标记 `passed`，依据两次同 VINS 二进制的独立力驱动冷启动、实际运动包 adapter 回放、既有断流／重启故障注入，以及两次独立零特征视觉退化注入。定位健康限值仍为 PROVISIONAL；GOAL A–H、Goal B/E/F、P3–P6 和最终飞行验收仍未完成。
- 视觉退化注入结果：保留输入时间戳、连续发送全黑图像，VINS 特征计数归零而 raw `solver_usable` 仍为 true；两次新的 epoch 均由 localization adapter 以 `input_features_insufficient` 锁定。此为调试故障注入，不是误差分数或真实相机退化分布证明。
- 待决问题：无；下一阶段按 P3 推进真值隔离的调试飞行链，并继续 P4 活动目标与地图故障验收。
- 证据：[P2 阶段出口审计](../../progress/evidence/p2-stage-exit-audit.json)、[视觉退化门控](../../progress/evidence/p2-visual-degradation-gate.json)。详细 run、输入与哈希在忽略目录 `artifacts/runs/p2-localization-visual-degradation-20261017-01` 和 `...-02`。
