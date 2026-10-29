# 2026-10-27 N10 #363：静态净空复算与障碍场景盘点

## 目标

继续 N10.3，用已有 #361 current gate-free PX4 run 离线补算静态障碍净空，并核实可复用的障碍／重规划实验工具范围；不启动新飞行。

## 结果

#361 的 PX4 世界不是空场：实际 SDF 来自 `simulation/worlds/ego.sdf`，包含23个非地面碰撞形状。对目标至 landed 全区间重算，真值样本最小包络净空0.352841m；扣除观测到的最大样本间包络运动后0.337908m。此结果不能当成连续动力学净空保证或正式阈值。

已有 `evaluate_n10_clearance.py` 可评估静态 SDF box/cylinder。`probe_n06_live_layout.py` 有动态障碍和替代曲线检测，但仅 planner-only、无 PX4/bridge 实际控制；当前 PX4 世界的动态注入接口也不能直接复用其 sensor_calibration service endpoint。

## 决定

N10.3 的静态净空不再是“完全没有数据”，而有 #357/#359/#361 三份可复算诊断数据；#362 本身未另跑 clearance evaluator。仍需补当前版长程 VIO误差／时效重复性，以及真实 PX4 执行中的动态障碍触发→EGO 替代轨迹→PX4 响应／落地证据。父 N10 继续 in_progress。详见 `progress/evidence/n10-clearance-static-world-replay-20261027-363.md`。
