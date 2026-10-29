# N08 #291：snapshot 前置拒绝，未发目标

## 结论

N05 扫描与任务前准入通过；N08 runner 在取得起飞 raw-map snapshot 前因 `trial_map_changed_during_snapshot_request` fail-closed。没有 action goal、bridge enable、取消或飞行数据，本轮不构成 N08 执行通过。

## 已通过前置项

- Run：`n08-cancel-translation-prescan-20261026-291`，VINS epoch `992d67a5d97244d8a774ba067ab64bfe`。
- N05 全机扫描完成 6/6；夹具拆除且 Gazebo model list 中已不存在；before/after/post-release 保持同一 epoch/map；post-release online/offline 结果一致并接受，`diagnostic_pass=true`。
- 40.004 s 只读 preflight 通过，最大 optimized odometry 接收间隔 0.116 s；当前区域 N05 online/offline admission 均接受。

## N08 拒绝点

`flight.json` 为 `FAIL`，failure=`trial_map_changed_during_snapshot_request`，`action_goal_sent=false`、`service_calls=[]`。native runner 在 `capture_snapshot()` 检查 MapStatus 后、请求 occupancy snapshot 前退出。旧实现先读取 MapStatus receipt time，再同步等待 snapshot service；服务发现期间没有显式 spin MapStatus 回调。代码顺序说明，缓存可能在等待后变陈旧；但 #291 没有记录 MapStatus 状态转移，因此不能排除当时实际 identity/readiness 变化。#292 已把服务等待移到新鲜度检查之前，等待新 MapStatus 后再验证 epoch、map、reset ack、input readiness 和 0.5 s receipt 门；真实 identity 变化仍拒绝，并写出具体观察值。

附加 `evaluate_odometry.py` 未产出报告，因为这次 runner 在运动前退出，`alignment-observation.json` 只有两条 attitude 样本、没有 raw 或 optimized odometry。这是前置拒绝导致的样本不足，不是时间戳回退。

## 安全读回

独立最终读回显示 bridge `DISABLED`、control disabled，PX4 disarmed 且 landed；`OffboardControlMode`、`TrajectorySetpoint`、`VehicleCommand` 均为 0。随后 `tools/project.sh stop n08-cancel-translation-prescan-20261026-291` 停止项目容器。

## 复核文件

- `flight.json` SHA256：`baa02b84f76ba2e0e534130e3f1737bebabf5fc453556003d288834bc1a27394`
- `n05-run-summary.json` SHA256：`0e46caba0d907a03133a06349261163d381de48b2cc5feb67025d0474af0c154`
- `safety-readback/final-px4-bridge-live.json` SHA256：`982f08aac4a667210f7fa1e75de2f05cee60c896d53ca20186a09785c1695e7c`
- `preflight.log` SHA256：`7862538d916b2f5ef3ac525466ccbe04752cfe2fa57a4922ffd01bb6452f6901`

完整原始结果保存在 `artifacts/runs/n08-cancel-translation-prescan-20261026-291/`。
