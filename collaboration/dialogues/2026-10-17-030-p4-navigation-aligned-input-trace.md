# 2026-10-17-030：P4 导航回调与独立输入时间线

## 任务摘要

继续 `GOAL.md` A–H、P0–P6；本次推进 P4 正常时钟活动目标 SIGINT 和导航回调空档诊断。

## 用户约束

- 以可复查运行证据推进；不得将关闭路径通过写成 P4 通过。
- 不修改旧实验来源；本轮不改生产源码、配置、时钟、freshness guard 或 EGO timeout。
- 最终组合禁止真值输入；本轮未启动控制器或 PX4，也未发布控制设定点。

## 决定

- #63 活动目标关闭路径通过，但 observer 时间线启动晚于此前导航回调空档；36条 EGO 输入告警均在轨迹 ABORT 后。
- #64 因 Fast DDS 无法映射 ROS domain 233 的端口，在传感器发现前退出，作为 precondition failure 保留。
- #65 因运动先于 VINS 静态初始化，定位持续 `propagated_stale`；无目标，不计入关闭路径。
- #66 将静态初始化、observer、导航和运动按序启动后，正常 canonical `/clock` 活动关闭再次通过。导航日志有419 ms优化里程计回调空档时，observer 同窗收到状态、里程计和 pose/depth 数据。
- #66 只将调查范围缩至导航节点接收／调度路径，不能区分 RMW reader 与 executor；两条 Destroyable 异常使 clean teardown 仍待确认。P4 保持进行中。

## 待决

- 导航进程何时观察 executor-ready、何时 take、何时进入 callback？长间隙来自 RMW reader、executor 还是 callback 内处理？
- 现有 freshness guard 和 EGO timeout 下，输入与导航回调能否稳定运行，并完成轨迹跟踪与到达？
