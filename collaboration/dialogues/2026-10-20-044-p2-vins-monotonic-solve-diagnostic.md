# P2 VINS 单调时钟求解时间对照 #287–#288

## 用户约束与决定

- 继续完成根目录 `GOAL.md` 并遵守AGENTS；保留工作区既有修改，不触碰只读实验来源。
- 仅在隔离VINS副本增加steady-clock诊断字段，保留原Ceres时间字段；不修改canonical遥测、定位健康门或控制路径。
- 通过同一帧 telemetry 对照两种耗时及主机realtime/monotonic偏移；不将单轮结果当作根因确认。

## 已确认结果

- #287先因run-local拷贝遗漏上游`../config`在安装阶段失败；补齐后fresh `camera_models`和`vins`构建通过。#287 planner run取得39条B-spline，但probe未保留新字段。
- #288修复probe字段白名单后复用同一instrumented binary运行，目标成功派发，捕获41条B-spline及644条无解析错误telemetry。排除10条求解前默认记录后，634组成对时长全非负；Ceres wall time比steady-clock短17–66 μs，中位数短约27 μs。
- 81.51秒主机时钟采样未见明显回拨；偏移变化范围14.737 μs。定位另因normalized cost略过1.0门槛锁定。EGO六条超时都重复报告sync_count=963、last occupancy update=36.648秒；同一源时间段MapStatus与适配器里程计仍前进，mapping gate约4.29秒后才因normalized_cost关闭。因此定位锁/清图不是先前超时的触发因素；EGO reader与callback/executor原因仍待区分。另有终点落入障碍的规划拒绝，无轨迹执行。
- 未启动PX4、轨迹服务器、控制器或真值源；无控制节点/话题。canonical VINS源码和健康门未改。

## 待办

- #284单次负时长仍未归因；保持健康门和阈值PROVISIONAL。
- 继续分开分析EGO同步超时与定位质量锁定，收集地图free/unknown、覆盖、持续规划及正式导航/避障证据。
