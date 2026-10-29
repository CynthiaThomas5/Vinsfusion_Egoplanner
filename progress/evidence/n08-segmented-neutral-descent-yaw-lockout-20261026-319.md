# N08 #319：回正前定位健康门锁定

## 运行结果

未武装支架扫描完成 12/35 阶段后，在 yaw=−π 向 yaw=−π/2 回转的 stage 12 中锁定。失败样本与期望 epoch 相同，`state=LOST`、`valid=false`、`reason=normalized_cost_exceeded`，归一化代价 1.007907。接收龄约 0.000056 s，源龄 0.044 s；最后记录的有效 trace 代价 0.998161。仿真 `/clock` 仍正常前进，因此本次不是时钟停滞。

剖面的前 12 阶段已完成，其中含远端观察、返回原点和 z=1 m 后向观察。它没有完成 yaw 回正，也没有进入中性视角分段下降；分段驻留假设没有被测到。此前 #312 的同一前 14 阶段曾越过对应转回段，但后续在连续下降中锁定。这一差异表明跨冷启动的定位状态需要进一步比较，当前数据尚不足以确定原因。

## 前置门与安全状态

初始 N05 在线／离线检查一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。没有释放后 N05、mission-current-area、只读 preflight、实时几何、N08 goal、control enable、取消或制动测量。

扫描器确认 fixture 已 detach/remove 且 LandDetector 为 landed。独立六秒 PX4／bridge 读回显示 bridge `DISABLED`、控制关闭、PX4 `DISARMED/landed`，控制模式、轨迹设定点和车辆命令计数均为零，车辆持续未解锁。Gazebo 模型列表中不存在支架 fixture。仅停止 #319 容器，退出码 0。

## 下一步

先用 #312 与 #319 现有原始记录对齐 stage 12 的相机／VINS 时间、特征与长轨迹数、偏置、求解代价和健康归一化代价，并确认起始健康差异。只有发现可检验且单变量的新路径时才继续支架扫描；不重跑 #319，不放宽门限。若没有可区分的证据，N08 保持未通过并说明缺失条件。

结构化报告与文件 SHA：[JSON](n08-segmented-neutral-descent-yaw-lockout-20261026-319.json)。原始数据：[run 目录](../../artifacts/runs/n08-cancel-highspeed-prescan-20261026-319/)。
