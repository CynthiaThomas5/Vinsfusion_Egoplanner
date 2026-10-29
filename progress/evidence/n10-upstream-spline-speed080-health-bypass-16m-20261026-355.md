# #355 N10.3 定位策略旁路诊断结果

## 结果

飞行动作和目标保持通过，但这不是完整验收通过。runner 为 PASS，单目标 action succeeded；独立真值评估的最小三维位置误差为 0.030 m，连续目标驻留 3.250 s，达到 3 s 标准。ACTIVE 保持完成 600.0 仿真秒，墙钟 785.7 s，RTF 0.764。PX4 实测位置速度峰值为 0.613 m/s。

旁路确实生效。normalized cost 最大值为 4.398，超过未改的 1.0 项目策略阈值；旁路保留了 cost 越线原因和原始质量历史。该结果只说明任务在这次诊断配置下继续执行，不给正式定位资格。

## 为什么总体不通过

真值与对齐记录器、bridge 阶段记录器和接触观察器均使用 380 秒墙钟上限；完整任务约 885 秒。接触评估因此没有观察到最终落地接触，报告为 passed=false、禁止接触事件 0、落地接触未观察到。该报告属于观测不完整，不能解释为实际碰撞，也不能作为零碰撞通过。raw odometry evaluator 因没有完整 PRESTREAM-to-LANDED 时间段而失败，calibration evaluator 缺少 odometry-evaluation.json，未能生成结果。

独立 6 秒 PX4/bridge 终态读回通过：phase=LANDED、landed=true、armed=false、control_enabled=false、vehicle remained disarmed=true、control samples zero=true。之后已停止本次项目容器。

## 结论与后续

#355 证明定位质量/源龄策略旁路能让这条 16 m 航线完成目标驻留和 600 秒 ACTIVE 保持；但不能用于定位健康资格、接触验收或关闭 N10。已修复 380 秒提前截断：#356 将只读观测延长到终态 flight.json，墙钟上限 1500 秒，并强制驱动核对所有观测器的终态标记。

原始文件在 artifacts/runs/n10-20261026-355-upstream-spline-speed080-health-bypass-16m/。机器可读摘要见 [JSON](n10-upstream-spline-speed080-health-bypass-16m-20261026-355.json)。
