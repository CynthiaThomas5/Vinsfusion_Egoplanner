# N10.3 #362：当前 gate-free runtime 高速取消停车重复协议

状态：**SITL 启动前冻结**。这是 #359 的同速窗独立重复，目标是确认当前移除项目定位健康门限后的 PX4 停车测量是否可复现；本次单样本仍不构成普遍停车保证。

## 假设与唯一主要变量

在 PX4 水平速度首次进入 0.50–0.56m/s 时由调用方取消同一条 16m EGO 目标，记录替代样条、停止带和真值停止路径。相对 #359，唯一运行策略变化是当前源码已删除项目自加的 VINS 质量/定位与优化里程计回执龄门限；#359 使用的是运行时旁路。路线、EGO 参数、速度窗、起点、spawn、PX4桥、官方碰撞规则及观察器保持一致。

## 保持不变

- EGO：max velocity 0.8m/s/轴，max acceleration 0.25m/s²/轴，planning horizon 5m。
- 一条 +16m ENU / +0.10m / +0.20rad 单目标；0.50–0.56m/s PX4水平速度取消。
- normalized cost、source age继续记录但不触发项目定位质量/定位回执龄锁存；历史1.0仅是离线对照。
- 保留 epoch/消息/时钟完整性、地图身份与 EGO 融合新鲜度、PX4桥控制/watchdog和 official_ego inflated-occupied 规则。
- 真值和 Gazebo contact 均只读，禁止进入控制。

## 有效量测判据

需要实际触发速度在窗内、caller-cancel被确认、观察到不同 trajectory id、PX4水平速度≤0.03m/s且垂直速度绝对值≤0.05m/s连续保持1仿真秒。PX4样本间隔≤0.20s、真值间隔≤0.04s、contact observer完整且禁止接触为0；独立末态读回必须确认 LANDED/disarmed/control-disabled/zero-control。缺一项就保留为不可量测/失败样本，不通过修改门限补救。

记录取消速度、EGO参考速度、取消确认/新轨迹延迟、真值停止路径与时间、1秒停止带内位移、减速曲线、normalized-cost、地图和定位时序、接触及终态。与 #359 对比只讨论测量差异；两个样本不足以推出一般制动距离或净空。

## 版本和运行命令

- Runtime contract：`fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`（665 个文件），与 #361 相同。
- runner SHA-256：`9c56b728c90f55c97500c76f36b18913e867b5367fad1fc08a95ad68deecd26b`。
- planner SHA-256：`0f92519ded6f367387998f01e19a27e270b94c7571e12fbe5b80f82b8ed7473e`；goal SHA-256：`0e275927089a9d04810d483fc6634717d6f7fcd15472a508601cbd5790600f00`。

启动 SITL：

```bash
D435I_N09_CONTACTS=1 D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed080_calibration.json D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json bash tools/project.sh sim n10-20261027-362-current-gate-free-speed050-cancel-repeat
```

栈就绪后运行取消测量：

```bash
docker exec d435i-n10-20261027-362-current-gate-free-speed050-cancel-repeat bash /workspace/tools/run_n10_cancel_calibration.sh n10-20261027-362-current-gate-free-speed050-cancel-repeat config/components/navigation/n10_long_range_vio_calibration_goal.json 0.50 0.56
```

独立 readback 确认 `safe-to-stop.json` 为 true 后再关闭容器：

```bash
bash tools/project.sh stop n10-20261027-362-current-gate-free-speed050-cancel-repeat only after safe-to-stop.json is true
```

机器协议：[JSON](n10-cancel-stop-gatefree-speed050-protocol-20261027-362.json)；运行前指纹：[runtime JSON](n10-cancel-stop-gatefree-speed050-runtime-prelaunch-20261027-362.json)；预期结果目录：`artifacts/runs/n10-20261027-362-current-gate-free-speed050-cancel-repeat/`。
