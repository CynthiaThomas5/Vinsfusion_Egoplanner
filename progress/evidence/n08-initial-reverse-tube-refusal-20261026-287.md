# N08 #287：实测初始回摆触发参考管道 watchdog

本轮按既有流程完成 N05 纯平移全机支架扫描 6/6、夹具移除、释放后在线／离线准入及 40.013 秒只读 preflight。mission 的当前区域准入、地面走廊、起飞后同身份地图的 25 个方向性 raw 查询球和终点候选降落几何均通过；25 个查询球内 unknown／occupied 均为 0。

EGO 接受了前向 0.6 m 单目标，但首条 B-spline 相对起飞后认证起点最低到达 **−0.002532 m**。临时 `x >= 0` 条款要求零回摆，故在全曲线检查时以 `reference_curve_left_certified_trial_tube` fail-closed；横／垂向偏差峰值 0.013682 m，速度导数上界 0.081575 m/s，都是原限值内。计划中的运动中取消尚未成为有效试验：没有 `cancel_stop_trace`、没有通过的实时 spline 证书、没有替换停止样条，也没有制动测量。observer 记录的 `caller_cancel` 是 watchdog 后的 action 清理，不是速度窗口内的受控测量事件。

runner 随后走既有安全降落路径。flight 记录及最终 PX4／bridge 独立回读均为 landed、disarmed、control disabled；回读窗口里没有 OffboardControlMode、TrajectorySetpoint 或 VehicleCommand 消息。项目容器已停止。该运行保留 FAIL，不计正常目标、取消或制动通过。

针对性离线复算确认：给启动瞬态最多 **5 mm** 回摆，同时将其计入方向性可达体积后，实测 spline 及同一 raw map 的 25/25 查询球、起点 hold 和全向终点 hold均通过。几何可达中心上界为 0.244340 m，允许上界 0.262500 m，仍有 0.018160 m 余量。完整 5 cm 参考横／垂向管道、0.25 m tracking margin、0.15 m tracking 上限、0.12 m/s 速度上限和 raw unknown／occupied 拒绝均保持不变。该复算只支持新的静态几何门，不是飞行通过证据。

明细见 [机器报告](n08-initial-reverse-tube-refusal-20261026-287.json)、[同图／同曲线复算](../../artifacts/runs/n08-cancel-translation-prescan-20261026-287/n08-bounded-initial-retreat-replay.json) 及 [#287 原始运行产物](../../artifacts/runs/n08-cancel-translation-prescan-20261026-287/)。
