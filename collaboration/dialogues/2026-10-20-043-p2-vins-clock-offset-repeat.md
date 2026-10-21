# P2 VINS 负求解时长复测 #286

## 用户约束与决定

- 继续完成根目录 `GOAL.md`，遵守项目协作约定；保留工作区既有改动，不修改旧实验来源，不改变定位健康门或PX4控制边界。
- 用当前固定镜像和planner-only运行重复#284，同时独立采样主机realtime与monotonic时钟偏移。
- 对Ceres/Linux时钟行为只记录为来源支持的候选机制，不把推断当作#284的已证实根因。

## 已确认结果

- #286运行成功，目标于5.715秒发送，ready地图902点，捕获27条B-spline；VINS telemetry 644条且无解析错误，未复现负 `solve_seconds`。
- 85.387秒内8470次时钟偏移样本的范围17.713 μs，最大相邻变化17.432 μs，未见明显向后跳变。#284没有这一监测，所以不能由#286回溯证明或排除其间出现时钟调整。
- #286后来因normalized_cost 1.0034失锁；EGO输入超时仍独立存在。没有控制节点／控制话题、PX4、运行时真值或轨迹执行。
- Ceres 2.2.0源码使用wall-time差分并在Linux调用 `gettimeofday`，说明系统realtime向后调整可构成候选解释。

## 待办

- 在run-local VINS副本测量 `steady_clock` solve duration，保持原始Ceres时间字段用于对照；不改canonical遥测契约、门控或阈值。
- 继续分别调查EGO输入同步和定位normalized-cost锁定；收集地图free/unknown、覆盖、持续性与正式导航/避障证据。
