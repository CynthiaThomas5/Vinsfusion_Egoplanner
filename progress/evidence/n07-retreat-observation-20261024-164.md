# N07.10 #164：返航阶段加速度 bias 门限复现

## 结果

- Run：`n07-20261024-164-01`，wall layout，路线 `n07_spawn_minus65_retreat_180_pitch045_return_view`。初始 fresh N05 online/offline 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。offline replay 与在线逐阶段结果匹配。
- 地面边界审计：raw-ground plane 为 z=−0.35 m；接触体积436个未知体素中心中，0个低于平面、52个在平面、384个高于平面；另有44个整格低于地面的单元已排除。HOLD 有566个未知中心，均在平面以上（z=0.45…1.25 m）。拒绝来自飞行体积内的未知空间。
- 支架路线完成5/9阶段，在返航 stage 5 的 sim=202.456 s 首次超过既有加速度 bias 限值0.15 m/s²（记录值0.150866）；该样本仍有111条 long tracks 和154个 stereo features。记录峰值bias为0.190352 m/s²。定位健康门触发并中止扫描；没有到达 `n05-prescan-ready`，自动观察器因此未启动attached N05检查。
- 支架确认脱离、移除且场景中不存在。最终 LandDetected=true（回执龄0.637 s），PX4 arming_state样本为1/DISARMED，bridge为DISABLED、控制关闭、未武装、landed=true；容器退出码0。无飞行，hover仍0/3。

## 判定与下一步

#164 没有取得 post-scan 或 released gate，不能用于飞行准入。下一轮 #165 采用同一 wall layout、spawn 与未武装支架流程，唯一主要变化为复用 #146 已验证并完整完成的 `n06_full_airframe_retreat_240_oblique_early_view` 路线；在 `n05-prescan-ready` 立即检查attached gate，随后释放支架并检查released gate。门限、包络与 N05 判据不变。只有 released 五阶段检查 online/offline 一致全通过，才在同一冷启动检查 PX4 EV fusion／唯一控制发布者并执行首个≥30仿真秒无目标悬停。

原始运行数据在 `artifacts/runs/n07-20261024-164-01/`；初始 N05 replay 和体素审计分别见[n05 replay](n07-n05-before-offline-replay-20261024-164.json)与[unknown audit](n07-n05-unknown-volume-audit-20261024-164.json)。
