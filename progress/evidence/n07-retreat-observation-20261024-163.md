# N07.9 #163：pitch 段 health 事件记录与路线复现

## 结果

- Run：`n07-20261024-163-01`；复用 #162 的9阶段 `n07_spawn_minus65_retreat_180_pitch045_return_view`。9/9阶段完成，actual fixture 路线回到 home，未解锁或起飞。
- 初始 N05 fresh online/offline 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。`z=-0.35 m` raw-ground plane 以下的 whole-cell 仍被排除；审计中 TAKEOFF_CONTACT 有436个未知中心（0个低于平面、52个在平面、384个高于平面），HOLD有566个未知中心、均高于平面（z=0.45..1.25m）。详见[unknown-volume audit](n07-n05-unknown-volume-audit-20261024-163.json)。
- 全量 `/localization/status` 记录共11,220条：8,040条 TRACKING，随后3,180条持续记录 `telemetry_stale`。首次锁存为 sim=335.152s，normalized cost=0.472924；最大记录 cost=0.718690，没有观察到 cost>1.0。2000条VINS telemetry的long tracks最低92、stereo最低124、加速度bias最高0.04262 m/s²。raw telemetry记录在health锁存后仍继续到sim340.432s，因此确切的送达／接收龄触发原因仍未定。
- attached N05 checker没有取得新鲜 optimized odometry，在120秒等待期限后留下结构化错误；没有产生attached快照，也没有post-release gate。不能把9/9阶段当作N05或N07运行通过。
- fixture已脱架移除并确认Gazebo模型不存在；320条PX4 LandDetected均true，所有VehicleStatus样本为DISARMED；清理末条LandDetected新鲜且通过。独立bridge状态`DISABLED`、控制关闭、未解锁、landed=true。容器Exited(0)。无飞行，hover仍0/3。

## 下一步

#164保持同一路线和判据，将attached/released N05检查由marker触发的主机监控流程立即执行，使用较短有界等待；同时去掉 keep-all 状态订阅以降低额外DDS负载。仅当released五阶段online/offline全通过，才继续同一epoch的N07前置核对和首个≥30仿真秒无目标悬停。

原始状态事件位于`artifacts/runs/n07-20261024-163-01/localization-status-history.yaml`，SHA256 `a1178be7d3f5dfeae502e0b7f37141d606dac8ac5b2c608be77e7c5d9dc6f4f2`。完整运行日志、VINS telemetry、odometry与输入manifest均位于同一 run 目录。
