# #364 N10.3 PX4 在线障碍重规划诊断协议

对话摘要：[2026-10-27 #364](../../collaboration/dialogues/2026-10-27-364-n10-dynamic-replan-protocol.md)

## 交付

冻结一个基于 #361 current gate-free runtime 的单变量 PX4 SITL 动态障碍协议：goal 后12仿真秒，在 `vio_initialization` 世界 `(0,0,1.4)m` 注入0.8×0.8×2.8m box，观察 raw map、同 goal/epoch 的新 EGO traj_id、PX4实际响应、净空、接触和 landed/disarmed/control-disabled/zero-control 末态。

协议明确定位健康门不恢复、无 raw-free 全曲线 gate，真值仅离线评估；1秒无替代轨迹时 caller-cancel 是运行诊断的停止流程，不是生产阈值。详见 [协议](../evidence/n10-live-obstacle-replan-protocol-20261027-364.md) 与 [机器协议](../evidence/n10-live-obstacle-replan-protocol-20261027-364.json)。

## 验证状态与下一步

仅完成协议冻结，没有创建 injector 或启动飞行。下一项 #365：实现 run-local 注入／只读观察脚本，核实 Gazebo 世界服务、时间戳和日志；冻结脚本哈希后，才按 #364 做 SITL。N10.3/N10 仍未通过。
