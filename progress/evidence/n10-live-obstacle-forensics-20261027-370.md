# N10.3/#370：#369 动态障碍任务离线取证

## 结论

#369 的 PX4/EGO 任务本身完成了 16 m 单程目标、目标后 600 仿真秒 ACTIVE 保持，并安全降落、解除武装、关闭控制。该 run **不能作为无碰撞任务通过**：独立接触记录发现机体与世界原有的 `unit_cylinder_4` 发生一次持续约 0.628 仿真秒的擦碰事件段，共 134 个接触消息，最大穿透深度约 0.000521 m。接触对象不是注入方箱。

同时，独立到达结果依赖评估时间窗：旧 `evaluate_arrival.py` 只评估到原生 action 回报成功，联合真值位置/yaw窗口为 2.200 仿真秒、2.759523 墙钟秒，低于 3 秒；N10 `evaluate_n10_arrival.py` 评估到落地，包含原生 action 返回后的 600 秒保持，联合窗口为 267.040 仿真秒、342.001 墙钟秒。前者没有证明原生成功回报时已独立满足 3 秒，后者证明之后的保持确实稳定。N10.4 必须将到达窗口与任务回报语义统一，当前不把这两个不同窗口合并成一个 PASS。

## 圆柱接触的可复算几何

- 世界 SDF 中 `unit_cylinder_4` 中心为 `(-2.75559, -2.44735, 0.5) m`，半径 `0.5 m`、长度 `3 m`，顶部 `z=2.0 m`。
- 首次接触在 `99.652 s`。将独立真值样本固定插值到接触时刻后，机体参考位置约为 `(-2.21752, -2.43231, 1.98600) m`；机体中心到圆柱轴线的水平距离为 `0.53828 m`，只比圆柱半径多 `0.03828 m`，机体中心也在圆柱顶面以下约 `0.01400 m`。
- 以同一固定地面 SE(3) 将 EGO `PositionCommand` 转换到世界 IMU 参考点，接触时参考点约为 `(-1.96507, -1.89900, 1.84826) m`；与插值真值 IMU 参考点相差 `0.51874 m`。对应命令轨迹中心到圆柱轴线为 `0.96208 m`。
- 因此，较大的参考到真值偏差足以解释为何实际机体接近圆柱而命令参考更远；这是有数据支持的调查方向，不足以单独认定最终根因。接触时刻没有保存圆柱附近的相机图像或 EGO occupied cloud，不能据此声称圆柱未被相机看到或地图漏检。

## 注入方箱与运行结果

- 方箱在目标开始后 12.000 s 获 Gazebo create ACK；记录到 7 个目标 ROI occupied-cloud 样本，最多 549 点，并观察到同一 goal/epoch 的替换 spline。离线方箱机体包络采样最小净空为 `0.54715 m`，扣除最大相邻样本包络运动后的值为 `0.46270 m`。这是对该方箱的采样下界，不覆盖静态圆柱，也不是连续动力学证明。
- #369 未出现先前的 `odometry_time_error` 或 alignment 数值降落故障。目标 action 成功，随后 600 仿真秒保持完成；末态读回为 LANDED、disarmed、control disabled、末态控制样本为零，容器已安全停止。
- 本轮没有找到新的项目自加运行时检查在接触前阻止或改写该轨迹。检查结果与接触报告均为只读；此前项目自加的整曲线证书、定位质量/源龄门和 alignment 平移/yaw 数值降落门分别已按用户授权移除。EGO 原生 inflated-occupied 碰撞规划、PX4 状态/时间完整性仍是被测链路的一部分。

## 下一步判别动作

N10.3/#371：保持 #369 的 runtime、目标、EGO 参数、场景、注入方箱与注入时刻不变，只增强只读观察，在预计接近 `unit_cylinder_4` 时记录相机深度/彩色帧、`/grid_map/occupancy` 圆柱 ROI 点数及同身份 occupancy sphere 查询。用这些数据判别圆柱是否进入可见深度/occupied 输入，并与记录的 EGO 参考和独立真值偏差对齐。观察器不得发布控制或改变任务；不按结果删改碰撞判断，不预设“漏检”或“跟踪”是根因。若复跑未重现接触，仍保留 #369 失败并将缺少复现记为未决。

## 输入与评估器哈希

完整原始数据保留在 `artifacts/runs/n10-20261027-369-alignment-gates-removed-live-obstacle/`。

| 输入 | SHA-256 |
| --- | --- |
| `flight.json` | `50f77b7015d15af6692b1c27f417f2badd843fb73f223a1713c1444f27a83cf1` |
| `arrival-evaluation.json` | `51a3896200999c390042d94dadbbcd006efb311fe11ae262601c02765b46839e` |
| `debug-truth-evaluation.json` | `04f5129bab7245351c2eca83eb2e2b54f8cde7d4fbf5270fe9373fbda60a21c8` |
| `vehicle-contact-evaluation.json` | `2674f212edaae2bc7540b5b9849dd0da3d23335928e30c600940625b88bc8124` |
| `n09-contact-observation.json` | `988af74b08d950661964d8b67ee9a8b4d24cc2bedc2464e1415a844dc184d57d` |
| `n10-calibration-evaluation.json` | `5d382c9f63075044925d79d3bf6b3752120c76ab43db933897890778dbda0d9b` |
| `n10-live-obstacle-box-clearance.json` | `99f01b1ea11087645591f3f1e89a1681922c42c297aa490df38b6da680a200b9` |
| `n10-live-obstacle-observation.json` | `10c16686291220fb406393692bea809d3aea3c49e47dcbfd6a504e91527db4fa` |
| `vio_initialization.sdf` | `cb57fdb46eb71dbffe002bc4ae96bebcdcaa774824231d83417aadcc8af9d5ca` |
| `planner-observation.json` | `aa861a9b0ec9c6257bd45e2e4457a79697e2759c83ff1eb6b2cd6071fe37cbed` |
| `tools/debug_truth/evaluate_arrival.py` | `8277438c973ae81267a2046b6b9652e1b4b96effd2766f4a5b9a50e2fd052d86` |
| `tools/debug_truth/evaluate_n10_arrival.py` | `701e77eee1f5a93b2dff2d55df4817957fa5d962c4cdb7b08603c58084d99fb8` |

本报告只复算既有归档，不是飞行通过证据；N10.3 与父 N10 保持 `in_progress`。
