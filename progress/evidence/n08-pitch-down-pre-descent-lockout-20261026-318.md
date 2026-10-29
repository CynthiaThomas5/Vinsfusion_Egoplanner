# N08 #318：俯仰动作在下降前触发定位锁定

## 运行结果

冷启动未武装支架扫描使用 `n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_pitch_down_descent`。前 14/19 阶段完成，包含 z=1 m 后向观察及回正。第 14 号索引阶段开始后约 3.4 仿真秒，在 yaw≈0、z=1 m 时，单独俯仰动作触发定位锁定；扫描器尚未开始下降。

失败定位样本为 `state=LOST`、`valid=false`、`reason=normalized_cost_exceeded`、代价 1.022938。样本与预期 epoch 相同，接收龄约 0.000048 s、源龄 0.140 s。最后有效轨迹样本为 z=1.0 m、yaw=0.0158 rad、pitch=−0.1217 rad，代价 0.977689。记录说明本剖面未完成，不能据此断言俯仰是唯一原因；此前 #312 的中性俯仰剖面完成转向回正，但在下降中触发同一健康门。

## 前置门与安全状态

本轮初始 N05 在线／离线回放一致拒绝 `ground_plane_insufficient_raw_occupied_voxels`。支架扫描失败后没有释放后 N05、mission-current-area、只读 preflight、实时几何、goal、控制 enable、取消或制动测量。

扫描器确认夹具已脱离、模型已移除且落地。独立六秒 PX4／bridge 读回为 bridge `DISABLED`、控制关闭、PX4 disarmed/landed、控制模式／轨迹设定点／车辆命令样本均为零，车辆在整个读回期间保持未解锁。只停止了本 run 容器，容器退出码 0。

## 下一项

#319 保留 #312 的前 14 阶段和中性相机视角；把 1→0 m 下降按 0.1 m 分段，并在每段之后保持两秒。每段移动时间按原 1→0.5 m 的 12 秒和 0.5→0 m 的 7 秒比例计算，唯一主要变量是每个小步之间增加驻留。若这仍触发定位门，则停止同类扫描变体并用源数据复盘，不能越过门限继续任务。

结构化数据与 SHA-256：[JSON 报告](n08-pitch-down-pre-descent-lockout-20261026-318.json)。原始记录：[run 目录](../../artifacts/runs/n08-cancel-highspeed-prescan-20261026-318/)。
