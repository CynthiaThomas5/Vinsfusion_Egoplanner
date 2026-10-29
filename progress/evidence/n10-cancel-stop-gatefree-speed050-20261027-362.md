# #362 N10.3 当前 gate-free runtime 高速取消停车重复

## 结果

按冻结的 0.50–0.56 m/s PX4 水平速度窗口，在当前移除项目自加定位质量／回执龄门限的 runtime 上完成一次 PX4 SITL caller-cancel 停车量测。评估器判定 `measurement_complete=true`、11 项检查全部通过；这是诊断样本，`formal_qualification=false`。caller-cancel 是本试验动作，故 `action_canceled=true`、`action_success=false` 属预期结果。

- 取消触发时 PX4 水平速度 **0.500180 m/s**，EGO 参考速度 **0.533871 m/s**。
- caller-cancel 确认延迟 **0.000996 墙钟秒**；替代 EGO 轨迹 **0.032 仿真秒**后出现。
- PX4 **6.76 仿真秒**后首次进入停止带，连续保持 **1.02 仿真秒**；52 个 PX4 样本，最大间隔 **0.028 秒**。
- Gazebo 真值从取消到停止带的水平路径 **1.260994 m**，水平端点位移 **0.990563 m**，三维路径 **1.261963 m**；真值最大间隔 **0.020 秒**，区间内 340 个样本。
- 停止带内 1 秒的真值最大水平变化 **0.015394 m**；取消过程观测到 PX4 水平速度最大值 **0.509662 m/s**，水平减速度 p10 **0.014112 m/s²**，首次出现 10% 速度下降用时 **1.30 仿真秒**。
- normalized cost 最大 **0.880384**；当前试验中没有超过历史 1.0 对照值，但项目定位质量／回执龄门限确实已移除（来源策略标记为 `removed`）。
- contact evaluator 通过，禁止接触 **0**；五类观察器均观察到终态记录。独立读回为 landed、disarmed、bridge control disabled、控制样本为 0；`safe-to-stop.json=true` 后项目容器已停止。

## 与 #359 的有限对照

旧样本 #359 触发速度为 **0.500241 m/s**、水平停止路径 **1.304474 m**、首次进入停止带 **4.96 仿真秒**。本次路径短 **0.043480 m（约 3.3%）**，但进入停止带慢 **1.80 仿真秒**；本次 p10 减速度也低于 #359 的 **0.026538 m/s²**。这些差异显示两次量测有运行变化，两个样本不足以建立通用停车模型、保证距离或净空限值。

本次运行世界包含静态障碍，但没有主动注入障碍或按该取消区间单独运行净空评估；因此**本报告没有量出障碍物最小机体净空**，零接触不能代替净空测量。也没有动态障碍重规划或故障注入证据。

## 版本、协议与复算产物

- 冻结协议：[#362 protocol](n10-cancel-stop-gatefree-speed050-protocol-20261027-362.md)。
- Runtime contract SHA-256：`fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`（665 files），与 #361 相同。
- Runner SHA-256：`9c56b728c90f55c97500c76f36b18913e867b5367fad1fc08a95ad68deecd26b`。
- Planner SHA-256：`0f92519ded6f367387998f01e19a27e270b94c7571e12fbe5b80f82b8ed7473e`；goal SHA-256：`0e275927089a9d04810d483fc6634717d6f7fcd15472a508601cbd5790600f00`。
- 原始运行目录：`artifacts/runs/n10-20261027-362-current-gate-free-speed050-cancel-repeat/`。
- 量测：`n10-cancel-braking-evaluation.json`、`n10-cancel-speed-curve.csv`；独立复核：`debug-truth-evaluation.json`、`vehicle-contact-evaluation.json`、`postflight-px4-bridge-readback.json`、`safe-to-stop.json`；身份：`runtime-contract.json`、`n10-cancel-run-manifest.json`。
- 机器可读摘要：[#362 JSON](n10-cancel-stop-gatefree-speed050-20261027-362.json)。

N10.3 继续未完成：仍需支持范围内的 VIO 误差／漂移重复性、障碍净空与动态重规划、故障退出时限及其物理依据。该量测不关闭 N10.3 或父 N10。
