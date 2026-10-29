# N10.3 #363：#361 静态障碍净空离线复算与场景盘点

## 范围

只读复用 #361 的已完成 PX4 SITL 记录，按其完整导航目标至 landed 时间段，用现有 `evaluate_n10_clearance.py` 对实际 Gazebo 真值、实际加载的 `vio_initialization.sdf` 和运行候选中的机体包络重新计算静态障碍间距。没有启动新仿真、没有改控制代码、真值没有进入导航或控制。

## 确认结果

- #361 并非空世界：`prepare_px4_vio_bootstrap_world.py` 将 `simulation/worlds/ego.sdf` 的静态场景合入 PX4 世界。该 run 的 `world.json` 确认实际加载 23 个非地面碰撞形状（4 个 box、19 个 cylinder）；地面 plane 按允许接触面排除。
- 命令：

  ```bash
  python3 tools/debug_truth/evaluate_n10_clearance.py \
    artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m \
    --world-sdf artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/vio_initialization.sdf
  ```

- 评估涵盖目标至首次 landed 的 **643.736 仿真秒、32,187 个真值样本**，最大样本间隔 **0.020 秒**。采样最小机体包络—静态碰撞几何间距为 **0.352841 m**；扣除本记录中观测到的最大相邻包络运动 **0.014933 m** 后，剩余 **0.337908 m**。
- 最近对象为 `unit_cylinder_2_clone`：圆柱中心 `(2.51998, -0.204252, 0.5) m`、半径 `0.5 m`、高度 `[0,1] m`；最小间距出现在真值位置 `(3.70114, -0.03770, 1.59191) m`。
- 该计算是当前仿真 SDF 与 provisional N05 外形包络上的离线几何测量。间隔扣减基于观测到的相邻样本运动，不是连续动力学上界；不涵盖未建模支架／线缆、实机尺寸误差或最终任务净空阈值。因此它补上了 #361 的静态场景净空数据，**不等于正式净空资格**。

## 场景和工具复用审计

- `tools/debug_truth/evaluate_n10_clearance.py` 可复算 PX4 完整任务对世界静态 box/cylinder 的样本间距；#357、#359 已有该 evaluator 产物，#361 本轮补算完成。#362 的 caller-cancel 专门量测尚未运行同一 clearance evaluator，不能把本报告数值移作 #362 结果。
- `tools/probe_n06_live_layout.py` 已有 Gazebo 静态箱注入、raw occupancy 观察及 EGO replacement/handoff 记录，但其运行范围明确为 planner-only：不含 PX4 bridge、trajectory server、navigation supervisor、控制发布或曲线执行。注入服务也固定指向 `sensor_calibration` 世界，不能原样当作当前 PX4 飞行中的动态障碍试验。
- 当前缺口已收敛为：需要在 PX4/bridge 实际执行链中观察一次新增障碍被 D435i/地图看到、EGO 发布替代轨迹、PX4 持续跟踪且无违规接触的闭环重规划；还需当前 gate-free runtime 的 VIO 长程误差／时效重复样本。无需另造一个静态世界才能复用现有净空工具。

## 输入身份与限制

- Runtime contract：`fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`。
- 实际 SDF：`artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/vio_initialization.sdf`，SHA-256 `cb57fdb46eb71dbffe002bc4ae96bebcdcaa774824231d83417aadcc8af9d5ca`。
- 机体包络源：`config/components/navigation/vehicle_envelope.json`，SHA-256 `2c76dc3e91aee1065e1f7095c29f93cb1bb79bdcaefd019ecfa333ff2a902d7c`。
- 评估器：`tools/debug_truth/evaluate_n10_clearance.py`。
- 原始运行：`artifacts/runs/n10-20261027-361-quality-gates-removed-speed080-16m/`；其中新增离线产物 `n10-clearance-evaluation.json`。
- 机器可读摘要：[JSON](n10-clearance-static-world-replay-20261027-363.json)。

N10.3 与父 N10 继续未完成。下一项先冻结 PX4 动态障碍／实际重规划的有界诊断协议，明确注入位置、独立观察信号、失败终态和安全停止条件后再启动；不将 planner-only #118/#126 等价为飞行重规划。
