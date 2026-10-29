#267：前向制动测得；原地转向因返航侧 raw unknown 被拒

## 准入与前向测量

本轮使用全新 SITL epoch `778678eaf1e142a997aae2576b5acfd7`，低速 planner profile 为 `n08_low_speed_trial.json`。全机支架扫描完成 15/15 阶段；支架释放后和 mission 当前区域 N05 均在同一 epoch/map_id 通过。40.003 s 只读 preflight 通过，最大 optimized-odometry 回执间隔 87.8 ms。扫描器仍报告泛化错误 `localization changed or became invalid during physical scan`；有效轨迹及后续 N05 通过与该错误矛盾，原因未明，继续保留警告。

N08 任务起飞后，0.6 m 前向 EGO 目标完成，在线连续样条管道证书通过。独立真值评估得到：参考峰值 0.08082 m/s、实际水平峰值 0.08100 m/s、实际三维峰值 0.08141 m/s。参考减速开始后，实机型 PX4 SITL 位置反馈用 0.288 m 水平路径距离降至水平速度不超过 0.03 m/s，并持续满足 1 s 停止判据；减速响应时间估计 0.844 s，最大参考跟踪误差 0.07862 m。该响应估计含 0.22 s 对称滤波。单次数据不构成三次 N08 资格通过，也不提供硬件保证。

## 转向拒绝原因

飞机在约 +x 航向停止，随后 180° 定点转向的 raw-map 前置检查拒绝了目标。转向点为 `(0.599, -0.003, 0.937) m`，所需 hold 球半径为 1.03062 m；新鲜 pre-turn raw map 查询到 5,637 个 free 体素、30 个 unknown、0 个 occupied，因此原因是 unknown，而不是已观测障碍。没有执行 yaw，也没有发出返航目标。

同一 hold 球在起飞前的 fresh ground map 中为 5,667 free、0 unknown、0 occupied。逐格对比显示，起飞前为 free 的 30 格在前向飞行后的 fresh pre-turn map 中变为 unknown；这些格集中在 `x=-0.45 m`、`y=-0.25…0.25 m`、`z=0.65…1.15 m`，位于此时机头后方。证据支持“飞行后当前后向区域失去已知 free 分类”，但不能仅凭这两张图断定是相机遮挡、局部地图更新策略或其它 mapper 原因。

候选位置离线复算：从停止点沿当前机头前移 0.22 m 的 capsule 有 9 个查询且均 raw-free；候选定点转向球也 raw-free。这个 0.22 m 定位动作只在归档地图上验证，不能授权飞行。归档图上尚未转头的返航 capsule 仍有 unknown；执行器必须先转向并取得更新融合图，再做返航 corridor 检查。

## 安全末态

任务总体为 `FAIL`，但飞行器已落地并解除上锁。直接 ROS 读回 PX4 `arming_state=1`、`landed=true`，bridge `LANDED`、`control_enabled=false`、`armed=false`、`landed=true`。`bash tools/project.sh stop n08-20261025-267-yaw-first-return` 退出码 0，项目容器已停止。未改变 unknown 门限、tracking margin 或速度上限。

## 关键文件

- [独立制动评估 JSON](../../artifacts/runs/n08-20261025-267-yaw-first-return/n08-braking-evaluation.json)
- [最终安全读回](../../artifacts/runs/n08-20261025-267-yaw-first-return/final-safety-readback.json)
- [飞行记录](../../artifacts/runs/n08-20261025-267-yaw-first-return/flight.json)
- [ground map](../../artifacts/runs/n08-20261025-267-yaw-first-return/n08-trial-ground-map.npz) 与 [pre-turn map](../../artifacts/runs/n08-20261025-267-yaw-first-return/n08-trial-pre-turn-map.npz)

SHA256：flight `a11df9269a601f0542c497eee76c71c9825b71915f477d9131c04b40800c301c`；制动评估 `63d8de4a61e9378d95ffe17f28e8cbc75fe3821a4c6273d488e28c517394492d`；ground map `245790e267cdf0586a6e7e49a42d2cdb05faa0d35e520bda3507a0796ffdd434`；pre-turn map `f04a8c000d3da161b5fa787630084afaa1bc311f177bc5a55d519caff315474f`；安全读回 `0d32554cec4e256edc8d1ebc3d277edcd95e3555d11940cab7b4c0131040bde1`。

**下一子项 #268**：保留已测的 0.6 m 制动段；只有当前转向 hold 球因 unknown 被拒时，先用新鲜 raw map 认证一个 0.22 m 前向 EGO 定位目标和候选转向球，再执行；动作后重新检查实际位置的转向球，原地转 180°，等待更新融合图，再认证机头前向返航并由 EGO 执行。任一阶段 unknown 都 fail-closed 并安全落地。
