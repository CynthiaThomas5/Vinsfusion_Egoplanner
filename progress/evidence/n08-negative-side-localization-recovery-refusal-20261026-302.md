# N08 负 Y 侧视到达但回收时定位健康拒绝（#302）

状态：新 profile 已到达 yaw −π/2 侧视并回中；在之后支架下降恢复阶段，VINS cost 越过原门限。未完成 fixture return，因此没有 post-release N05 或 mission。

## 结果

- profile `n08_overhead_free_sector_with_negative_side_view` 完成 15/18 阶段。stage 12–13 实际到达并保持 yaw −π/2；stage 14 回中 yaw 0 完成。随后开始从 z=1.0 m 回收至 z=0.5 m，VINS `normalized_cost` 达 1.025847，超过既有 1.0 门并停止；终止原因是 `normalized_cost_exceeded`。负侧视阶段最终有效 cost 曾达 0.7966。没有放宽健康门。
- 初始 N05 raw map 仍拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；健康停止后未产生 post-release map。
- fixture cleanup verified detached，Gazebo 中 fixture model absent，fresh land detector landed。独立 PX4 probe 4 秒确认 bridge `DISABLED`、armed/control disabled=false、PX4 disarmed/landed、控制消息0。定位锁存为非 tracking；项目容器安全停止 Exit(0)。

## 解读与下一步

负 Y 侧视视角本身已到达，所以 #302 不支持“无法侧视”；真正阻止进入 N05 的是侧视后立即开始支架下降回收时的 cost 越线。#303 只在侧视 yaw 回中后、保持 z=1 m 的 neutral pose 增加 15 秒再开始下降；扫描姿态、视角 dwell、布局、门限和 N08 mission config不变。检验这个回中窗口是否让 VINS 恢复到允许安全回收的健康状态。只有完成释放、同身份 post-release/current-area N05和 N08 corridor 全 free 后才飞。

机器可读状态、SHA 与 stage 证据见此 JSON；原始运行位于 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-302/`。
