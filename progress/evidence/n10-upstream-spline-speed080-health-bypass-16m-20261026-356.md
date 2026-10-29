# #356 N10.3 完整观察诊断结果

## 任务结果

五类观察器都观察到了终态 flight.json，墙钟观测约 58.5 秒；落地接触评估通过，禁止接触事件为 0，最终地面接触已观察到。raw VIO 离线误差报告完整生成。

flight runner 为 FAIL。EGO 在飞行约 2.60 m 后以 planner_full_curve_planning_failed 终止目标；真值评估的最小目标位置误差为 13.749 m，目标驻留为 0 秒，600 仿真秒保持未开始。独立 PX4/bridge 读回确认 LANDED、landed=true、armed=false、control_enabled=false、vehicle_remained_disarmed=true、control_samples_zero=true；项目容器 exited 0。

## 失败分类

EGO 运行日志记录多轮候选轨迹 collided、后续 plan_success=0/refine_success=0，随后从 REPLAN_TRAJ 转到 WAIT_TARGET 并报 planning_failed。碰撞策略仍为官方 inflated occupancy。定位旁路状态被观察到，但本次最高 normalized cost 约 0.644，低于未改的 1.0 阈值，故不是定位质量门导致。日志没有保存发生碰撞的精确体素，尚不能区分是真实障碍还是地图误占据。

## 可用校准数据

- 起飞前 raw VIO 对真值：位置 RMSE 0.0116 m、p95 0.0216 m；yaw p95 0.254°。
- 已执行段的 EGO 参考到真值跟踪误差 p95 0.528 m，超过现有 0.15 m 候选值；该候选门限并非最终冻结标准。
- goal 到 landed 段 map source/occupancy age 最大值分别为 0.164s 和 0.112s。
- 接触观察完整，禁止接触为 0；本次没有受控制动测量。

这些数据支持已观察时间窗内的定位、跟踪、地图时效和接触测量，不能关闭 N10.3，也不能证明全 16 m 路线或 600 秒保持。

## 后处理问题

冻结运行驱动没有把分析器脚本复制到 run 目录，在线分析因此报文件缺失。容器安全停止后，我从冻结准备目录补入相同 SHA 的分析器并离线运行，生成 n10-calibration-evaluation.json；指标和输入哈希已保留。后续驱动需在启动时显式复制分析器并校验 SHA。

原始产物位于 artifacts/runs/n10-20261026-356-upstream-spline-speed080-health-bypass-16m/。机器可读摘要见 [JSON](n10-upstream-spline-speed080-health-bypass-16m-20261026-356.json)。
