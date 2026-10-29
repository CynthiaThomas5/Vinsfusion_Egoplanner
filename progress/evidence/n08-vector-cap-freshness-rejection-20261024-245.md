# N08 #245：PX4 时间域有效，定位 freshness 拒绝 compute-only

## 结果

- Run：`n08-20261024-245-low-speed-vector-cap`。启动 manifest 使用目标低速 planner `config/components/mapping/n08_low_speed_vector_cap.json`，`max_velocity_m_s=0.075`。
- N05 支架扫描完成 16/16；before gate 仍按未知体素拒绝，after、post-release 与 current-area online/offline gate 在同一 epoch/map 接受。helper 的 `localization changed or became invalid during physical scan` 警告保留。
- PX4 时间域观察 423/423 样本有效，HRT 与 `/clock` 差 −0.128…+0.012 s，0 次时钟回退。故此 run 没有复现 PX4 时钟失配。
- Compute-only 在 enable 前因 `localization_or_px4_freshness_not_stable_before_enable` 被安全拒绝；LocalizationStatus 约 1.507 s 锁存 `telemetry_stale`。锁存快照里的 telemetry 与 optimized source age 均为 0.372 s，当前 health.json 上限为 0.300 s；normalized cost 为 0.85944，未越过 1.0。
- 独立 source observer 随后持续看到 raw VINS telemetry/optimized 前进至约 60.6 s、source stamp 607.600 s；adapter optimized/propagated 输出停在 1.390/1.395 s。现有证据能确认 stale 门触发并 fail-closed，但还不能确定为什么新 raw 样本没有在锁存前被 adapter 接受／处理。不能把它归因为 PX4 时钟或直接归因为主机 CPU。
- 没有 action goal、READY 曲线、PositionCommand 或 XY；stop-corridor certificate 因没有同 run 曲线而未能评估。

## 安全收尾

最终实时读回为 DISARMED、landed/at-rest、桥接 DISABLED 且控制关闭、夹具模型缺席。`bash tools/project.sh stop n08-20261024-245-low-speed-vector-cap` exit 0；容器 `Exited (0)`。详见 [final readback](../../artifacts/runs/n08-20261024-245-low-speed-vector-cap/final-safety-readback.json)。

## 判断与后续

“已通过项不复测、三次独立运行不要求连续”仍适用于 N07 的累计通过证据；它不改变同一次运行必须满足的 PX4 时间域有效、定位源龄、轨迹切换连续性或 N08 制动出口。#245 的失败和 N07 的既有通过互不抵消。健康源龄上限保持原值。

下一子项 N08.2ai #246：只读关联 `vins_telemetry`／`raw_optimized`、adapter 接收、`/clock` 与 status 回调在约 1.39–1.51 s 的先后顺序，并审阅订阅 QoS／executor 调度；先确认是否存在传输／回调积压或采样观测空洞，再提出最小修复。暂不重跑 N07，也不重复无针对性的飞行尝试。N08 保持 `in_progress`；实际低速 XY、停止距离／减速度／响应延迟及至少三次同版本目标运行尚未验收。

机器证据与源文件 SHA-256 见本报告对应 [JSON](n08-vector-cap-freshness-rejection-20261024-245.json)。原始产物位于 `artifacts/runs/n08-20261024-245-low-speed-vector-cap/`。
