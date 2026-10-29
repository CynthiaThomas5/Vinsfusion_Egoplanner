# N07.8 #162：俯视保持到返程结束

## 结果

- Run：`n07-20261024-162-01`，DISARMED 支架观察；未解锁、未起飞。
- 初始 N05 在线与独立离线结果一致拒绝：`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。raw-ground 平面 `z=-0.35 m`。只读未知体素审计显示 HOLD 包络 566 个未知中心，范围 `z=0.45..1.25 m`，位于地面以上；TAKEOFF_CONTACT 的 436 个未知中心中，0 个中心低于平面，52 个在平面，384 个高于平面。检查器另将 44 个完全低于平面的单元计入 `subground_excluded_cells`，没有把它们当作飞行空间。完整坐标与快照来源见[unknown-volume audit](n07-n05-unknown-volume-audit-20261024-162.json)。
- 支架扫描仅完成 3/9 阶段；pitch 转入未完成，最后健康 trace 在 `sim=148.744 s`、目标 `+0.201 rad`、实际 `+0.193 rad`。锁存状态为 `normalized_cost_exceeded=1.138230`。所记录 883 条 VINS telemetry 的同公式峰值为 `0.694196`，最低 long tracks 为 56、最低 stereo features 为 126、最大加速度偏置为 `0.10082 m/s²`。具体触发 telemetry/status 事件未被保留，根因未定。
- fixture 已 detach 并移除，Gazebo 模型列表确认不存在；PX4 状态样本全部 DISARMED，135 条 LandDetected 样本均 `landed=true`，末条新鲜确认通过。清理后独立查询为 bridge `DISABLED`、无控制、未解锁、`landed=true`、定位无效。容器 `Exited (0)`。没有 post-scan N05 检查，因此俯视路线对占据图的影响未知；hover 计数仍为 0/3。

## 结论与下一步

#162 未支持或否定“返程持续俯视”假设，因为扫描在该路段前就因健康锁存中止。地面以下单元已排除，当前拒绝来自地面平面及其上方仍未知的入口体积。下一轮应保存每次 LocalizationStatus 事件，并以更慢 pitch 转入/复位重复相同路径；不改 N05 判据或健康门限。

## 产物

- Run 原始数据：`artifacts/runs/n07-20261024-162-01/`
- 初始 N05 在线报告：`n05-before/n05-live-entry-check.json`，SHA256 `fb95aeb40a76a3322d9470c69abc90ba3c9f60f906a57aff19d94f2600b58602`
- 初始 N05 离线回放：`n05-before/n05-offline-entry-replay.json`，SHA256 `14fe404004ab44867617a0101b15905b43373bc13cb0018a476d620826a2e08d`
- 支架结果：`fixture-result.json`，SHA256 `e5bd34f7538cb4d698f0381cdf9a7f76c8c62d4c93779ee766a820a7e5e2f071`
- route / VINS trace：`fixture-trace.jsonl` `461eaf1c8601b052b0d24e6d24b8ed477ab2ee6bb548df83ca4a70393120117c`；`fixture-vins.jsonl` `4e4b19fcf8ed3d943f13d385ae0dcafd8af09035324106d9036ab77cb1c0487e`
