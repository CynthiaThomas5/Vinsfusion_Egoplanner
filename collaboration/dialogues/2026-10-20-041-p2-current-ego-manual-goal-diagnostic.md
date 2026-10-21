# 当前锁定 EGO 手动目标与健康时间线诊断 #282–#284

## 用户约束与决定

- 继续推进根目录`GOAL.md`，遵守项目AGENTS约定；原有 staged/dirty 工作区内容属于用户，不回滚、不混入暂存区，不修改旧 PX4/ROS 来源。
- 只做单 D435i 仿真链路的planner-only诊断。运行目标探针不启用轨迹服务器、控制器、PX4 bridge或setpoint发布者；不得将内部EGO FSM状态解释为飞行或轨迹执行。
- GOAL F净空门槛尚未冻结；此轮只记录诊断，不更改健康阈值、不把Goal或里程碑标记通过。

## 决策与已确认结果

- #282因目标探针启动前`right_stale`锁定、地图清空，没有有效目标前置条件，排除于规划结果。
- #283在定位TRACKING和ready MapStatus下发送一个目标并收到一条匹配epoch的B-spline。离线计算的名义球形机体余量为箱体0.574 m、圆柱1.640 m；定位后来以`normalized_cost_exceeded`关图。
- #284保持健康时间线采集62.863秒，目标在6.827秒发送；ready地图有921个占据点和15,569个膨胀点，记录8条B-spline。首条固定尺度SE(3)对齐使用310个时间配对样本，位置RMSE5.758 mm、P95 9.030 mm，箱体／圆柱名义球余量0.619/1.630 m。没有轨迹执行。
- #284唯一负solve计时样本在47.473168秒，为−0.544872秒；当时normalized cost=0.79756、solver usable。定位于47.508421秒以`solve_seconds_exceeded`锁定；整轮normalized cost峰值0.96617，未越当前1.0门限。代码检查和VINS telemetry patch说明负计时会触发现有0.1秒质量门，但该负值底层原因及可重复性未知。
- #284更早的EGO日志显示8次depth/pose同步超时；首条为`now=12.673`，同步计数130。尚无证据把早期EGO停顿与之后的定位锁定联系起来，后续分别诊断。
- #284没有控制节点或控制话题。容器数据采集和graph快照完成；首次宿主包装器因容器创建文件所有权导致离线输出覆盖失败。移除占位文件后宿主SciPy 1.8.0评估成功；修复wrapper并做shell语法检查，没有重新跑仿真。结构检查、两项shell语法检查、staged/unstaged diff check及三份run-report和38个原始文件哈希核验均通过。

## 待决问题

- 一条Ceres solve_seconds遥测为何产生负值，能否独立复现？保持fail-closed门控，不调整阈值。
- EGO更早的occupancy/pose同步停顿原因是什么？与后续定位质量门的关系仍未知。
- 在线free/unknown分类、地图覆盖/持久性、持续规划、轨迹跟踪、正式净空门槛及多轮冷启动验收仍未完成。
