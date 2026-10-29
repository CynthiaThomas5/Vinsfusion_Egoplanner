# 2026-10-27 #381 N10.3 raw VINS 速度量测

## 摘要

用户授权继续完成 N10。检查 #376 长航段归档后发现 raw VINS odometry observer 只存位置和姿态，没有保存 twist 速度。核对 VINS 上游 `visualization.cpp` 后确认，发布的 `twist.linear` 直接来自 `estimator.Vs`，以 VINS world frame 表达。

## 本轮决定

- 只扩展只读 alignment observer，保存 raw VINS 世界系线速度，并加一个离线速度误差分析工具。
- 真值使用仿真 D435i IMU 原点，固定一份 prestream scale=1 刚体对齐，使用 N01 full-state evaluator 已有的0.2仿真秒中心差分与0.04秒真值插值支持限制。
- 将误差拆成目标飞行/驻留、目标后 ACTIVE hold、PRESTREAM至 LANDED；阈值不在本次提前设定。
- #381 固定 #376 的 spawn、planner、goal、动态箱体、静态 cylinder 观察和飞行行为；唯一变量是只读测量字段与离线分析。无新增 health/speed gate，无控制者变化。

## 当前状态

准备阶段两工具语法检查、run-local Bash 语法、冻结哈希和 `tools/project_status.py` 均通过。Runtime-contract 为 `547082a4538a871dd3c3b9b26c0f6b45369fa18bf1b73a8d93f219ef3e537cce`。此后 #381 SITL 按冻结配置完成：16 m action 成功、独立 simultaneous position/yaw dwell=3.055 wall s、600 sim s ACTIVE hold 完成，raw velocity truth pairing=100%，无违规接触，末态安全读回且项目容器已停止。

原始 VINS PRESTREAM→LANDED 为 673.596 sim s／27.650 m 真值路径；位置 error P95/max=0.439/0.458m、yaw=6.585/6.869°，全程10s RPE平移 P95=0.0417m、yaw P95=0.3005°；goal-motion速度error P95=0.0282m/s，精确600s hold P95=0.0070m/s。目标保持的独立真值位置误差在226.096仿真秒后首次越过0.30m球，表明不能用短窗口RPE代替长程绝对漂移。

冻结速度报告将目标后到 LANDED 的605.352s标为 hold。保留原报告，新增离线分段复算器，以准确600s hold与5.352s着陆拆开，并复用N01 `_rpe` 补齐1/5/10s SE(3)误差；arrival同时位置/yaw驻留复算与原 `evaluate_arrival.py` 一致。当前结果详见[#381报告](../../progress/evidence/n10-vins-velocity-full-route-result-20261027-381.md)，run归档在 `artifacts/runs/n10-20261027-381-vins-velocity-full-route/`。

当前状态：#381测量子项完成；父N10仍 `in_progress`。下一步N10.3/#382整合指标来源、候选数值和适用范围，不新增运行时健康门；随后N10.4–N10.7继续按原计划。

- Protocol：[n10-vins-velocity-full-route-protocol-20261027-381.md](../../progress/evidence/n10-vins-velocity-full-route-protocol-20261027-381.md)
- Prelaunch：[n10-vins-velocity-calibration-prelaunch-20261027-381.md](../../progress/evidence/n10-vins-velocity-calibration-prelaunch-20261027-381.md)
