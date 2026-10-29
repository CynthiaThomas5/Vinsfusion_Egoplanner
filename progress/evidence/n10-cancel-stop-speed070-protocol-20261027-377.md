# N10.3 #377：基于已测峰值的 caller-cancel 制动量测

状态：**SITL 启动前冻结**。候选仅用于量测 PX4 实际速度达到已观测高速度区间时的取消响应；不设置飞行限速，也不新增健康门。

## 假设与唯一变量

#376 在同一 horizon5／0.8／0.25 配置下测得 PX4 水平峰值 0.7418 m/s；历史 0.70–0.80 m/s 区间有 98 个有效 PX4 样本。假设 caller-cancel runner 可在 `[0.70,0.80] m/s` 的首个匹配样本触发，并完整测出停止响应。唯一变化是制动量测触发速度窗；路径、planner、spawn、停止带、observer 和 current runtime 固定。#359/#362 的较低速样本作为历史参考，不作单变量因果对照。

## 运行条件和有效量测

- planner `config/components/mapping/n10_horizon5_speed080_calibration.json`：max_vel 0.8 m/s/轴、max_acc 0.25 m/s²/轴、horizon 5 m、`official_ego`。
- spawn `config/components/simulation/n10_long_range_spawn_minus8.json`：`[-8,0,0.3,0,0,0]`；单程目标 +16 m / +0.10 m / +0.20 rad。
- 速度窗 `[0.70,0.80] m/s` 只挑选接近实测峰值的停止样本，不限制控制速度、不作为验收阈值。
- 有效量测要求：触发速度在窗内；caller cancel 被确认；观察到新 EGO traj_id；PX4 水平速度 ≤0.03 m/s 且垂直绝对速度 ≤0.05 m/s 连续保持 1 仿真秒；停止期间 PX4 最大样本间隔 ≤0.20 s；真值最大空档 ≤0.04 s；contact observer 完整且零违规接触；独立末态读回 landed/disarmed/control-disabled/zero-control。
- 只读真值不参与控制。保留 PX4 原生预检、桥接状态机、官方 EGO inflated-occupied 碰撞处理、时间/epoch/map 身份约束。

运行前协议 JSON：[n10-cancel-stop-speed070-protocol-20261027-377.json](n10-cancel-stop-speed070-protocol-20261027-377.json)；prelaunch：[n10-cancel-stop-speed070-prelaunch-20261027-377.json](n10-cancel-stop-speed070-prelaunch-20261027-377.json)。
