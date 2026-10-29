# N08 #301 侧视路线定位健康中止

- 唯一变量：新冷启动的 N05 profile 使用 `n08_overhead_negative_side_view`。
- 结果：支架路线 7/16 阶段时 cost 1.058738 超过原有 1.0 门，锁存 `normalized_cost_exceeded`。尚未达到 yaw−π/2，因此没有负侧视图，也没有 post-release N05 或 mission。
- 安全：夹具 detach/remove 并确认 scene absent；PX4 未解锁且 landed，bridge DISABLED；独立 4s 读回 control-mode/setpoint/vehicle-command 为0；停止项目容器 Exit(0)。定位因健康拒绝未 tracking，未带旧定位继续任务。
- 决定：#302 以 #300 N05 通过 profile 为基线，仅插入起点附近 yaw−π/2 侧向观测和回中，不复用长返程；全部门限保持。
