# N10.3/#367 动态障碍重规划重测

- 约束：Goal完成模式继续N10；单D435i、Gazebo/PX4 SITL；复用patch 0053与#364冻结场景；用户要求检查项目自加保护，但只移除直接阻断且无官方依据的附加门。
- 运行：#367在goal后12.008s插入方箱，Gazebo ACK；传感器/EGO占据云观测到表面；同goal/epoch后续出现266条轨迹。
- 结果：动作`goal_timeout`，不是EGO planner abort。PX4 bridge在sim129.264s因`external_odometry_stale`进入降落。晚到VIO源时间128.968s，当前sim129.264s（差0.296s）；0.345s墙钟龄符合0.35s源龄限值，但64样本`/clock`历史覆盖仅约0.256s，映射拒绝`source_stamp_outside_clock_history`。
- 实际体包络箱体净空调整采样下界0.982m，零违规接触；独立PX4读回确认安全落地。校准error evaluator因flight record缺少完整PRESTREAM-to-LANDED记录未通过。
- 决策：不删除PX4桥失联降落，不放宽时间或龄阈值；单一变量增大历史缓存至128，正确插值已允许的0.296s源时间。下一步#368做同场景PX4 SITL复测。
- 报告：`progress/evidence/n10-live-obstacle-replan-retry-20261027-367.md`。
