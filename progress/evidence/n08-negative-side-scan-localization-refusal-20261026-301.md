# N08 负 Y 侧视支架扫描定位拒绝（#301）

状态：支架扫描在到达负 Y yaw 观察阶段前被原有 VINS 健康门停止。未取得 post-release N05 结果，没有 mission 或 flight。

## 结果

- 新冷启动布局 `n08_overhead_calibration`，使用既有 `n08_overhead_negative_side_view`，路线在第 7/16 段停止。最后 VINS `normalized_cost=1.058738`，超过原 1.0 门限；LocalizationStatus 锁存为 `normalized_cost_exceeded`。本 profile 的 yaw −π/2 观察未执行。
- 初始 N05 online/offline 同图拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`，所以没有可复用的 mission admission。
- fixture 已 verified detach/remove，Gazebo model absent，PX4 landed/disarmed。停止后 4 秒独立读回确认 bridge `DISABLED`，armed/control_enabled=false，PX4 arming_state=1、landed=true，控制 topic 消息0。定位已因 scan health gate 不再 tracking；按流程停止项目容器，Exit(0)。

该结果说明这条长路线在本冷启动会触发既有定位健康拒绝；不表示负 Y 侧视已证伪，因为路线未到该阶段。没有改变 cost 门限。

## 下一子项

#302 以 #300 已通过的 `n08_overhead_free_sector_view` 全路径为基线，只增加一次靠近起点的 yaw −π/2、pitch 0 侧视及回中阶段；保留原来可获得 N05 五阶段准入的平移、上视和正侧／下视。这样直接针对 #300 量到的负 Y unknown 区域，同时避免再使用 #301 长距离回程组合。布局、所有 admission threshold 和 N08 试验速度／停车包络不变。

JSON 哈希与原始日志位于此报告和 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-301/`。
