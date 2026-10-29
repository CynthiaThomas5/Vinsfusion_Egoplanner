#262：N08 起飞入口因机体包络 unknown 拒绝

## 结论

本轮没有起飞，也没有发出 EGO 目标。全新运行的 N05 当前区域检查在 `TAKEOFF_CONTACT` 以 `raw_unknown_in_expanded_vehicle_envelope` 拒绝；同一快照离线回放给出相同结果。当前 N05 规则检查完整机体包络和垂直起飞／保持路径，因此即使计划只垂直上升，落在该包络内的后侧未知空间也能阻止起飞。它不是只按计划的平移方向检查。

这证明本次有机体包络内的未知格子，不证明它们全由 D435i 后向盲区造成。只读体素审计中，odom 坐标 `x < 0` 半区在接触包络有 331/436 个 unknown 中心，在 HOLD 有 362/566 个；起始机头 yaw 约为 0，因此该半区近似对应机尾方向，但精确视场／遮挡根因仍需单独归因。所有原始 unknown、freshness 和健康门保持不变。

## 运行与准入

- Run：`n08-20261025-262-yaw-first-return`；当前源码与 #261 构建的全新 SITL。
- `preflight.json` 通过，但 mission 启动后的 fresh N05 当前区域检查拒绝；首个过早的 mission 调用因 stack 尚未启动退出，等待 `stack-started` 后在同一运行正确重试。
- 快照／深度源／融合／状态接收龄分别为 0.092／0.144／0.032／0.160 秒，均低于 0.4 秒门限；raw ground plane 有效，z = −0.35 m，110 个 raw occupied 地面候选体素。
- `TAKEOFF_CONTACT` unknown 436、occupied 0、地下排除 44；`ASCENT` 每个采样均拒绝，最大 unknown 592；`HOLD` unknown 566。41/41 阶段采样未接受。在线与离线拒绝身份及原因完全相同。
- 桥保持 `DISABLED`，PX4 `armed=false`、`landed=true`、`control_enabled=false`；`control_or_goal_published=false`、`truth_subscribed=false`。没有 `flight.json`。`bash tools/project.sh stop n08-20261025-262-yaw-first-return` 安全停止，退出码 0，当前无运行中的项目容器。

## 复算与证据

只读枚举命令：

```bash
PYTHONPATH=tools python3 tools/debug_truth/audit_n05_unknown_volume.py \
  --live-report artifacts/runs/n08-20261025-262-yaw-first-return/n05-current-area/n05-live-entry-check.json \
  --output /tmp/n05-unknown-volume-audit-262.json
```

在线拒绝报告 SHA256：`3bc69fdb893f160bc719bc4428a63266a9ae3b2587ea2916c9ba42decd05223d`。原始地图 SHA256：`df7852d4228cef448991cec82db6a979d8c6918b27667ab339262ce8ffa8e4f7`。完整运行目录在 `artifacts/runs/n08-20261025-262-yaw-first-return/`。该运行目录由容器以 root 创建，因此审计 JSON 保存在 `/tmp`，本报告记录可复算摘要。

作为对照，#260 使用新鲜 N05 支架扫描（布局 `n08_overhead_calibration`、profile `n08_far_small_pitch_view`）后，释放后的五个准入阶段曾全部接受。下一轮 #263 将在新 run 中重做同一支持扫描和释放后 fresh admission；只有该轮当前地图再通过 mission 前置检查，才执行“前向制动→原地转向 180°→转向后新鲜地图→EGO 前向返航→落地与独立方向评估”。不复用 #260 地图，也不绕过本轮拒绝。

本结果只回答 N05 对垂直起飞包络的当前行为；它不是起飞／飞行通过证据，N08 仍为 `in_progress`。
