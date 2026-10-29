# N08.2q #227 任务摘要

- 用户约束：当前 Goal 范围为 N08；不复测 N07 已通过的三次独立冷启动；本轮不执行 XY。
- 已有基础：#225 compute-only 生成／取消／保持与 N05 fresh admission 通过；#226 显示现有 B-spline 超过 0.15 m/s 门，起点 terminal-hold 有 unknown，PX4 水平参数／动态制动下界未记录。
- 本轮决定：只降低 EGO 每轴速度上限至 0.075 m/s，检验实际向量速度凸包是否 ≤0.15 m/s；用同 run B-spline 和 raw occupancy 做完整曲线及首尾 hold 几何复核；只读补齐 PX4 水平参数 boot-time 回读。
- 待决：若曲线／地图门不通过，保持 execute 锁定；后续针对明确失败查询设计新的只读观测或速度 profile，不用地面区域、旧 map 或参数最大值推导制动通过。
