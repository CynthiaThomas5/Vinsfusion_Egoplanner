# #359 N10.3 高速 caller-cancel 停止量测

## 结果

按预先冻结的 0.50–0.56 m/s PX4 水平速度窗口运行单 D435i Gazebo/PX4 SITL。运行评估器为 `measurement_complete=true`，所有 11 项诊断检查通过；该结果是一个诊断样本，`formal_qualification=false`。

- 取消触发时 PX4 水平速度 0.500241 m/s，EGO 参考速度 0.530167 m/s。
- caller-cancel 确认延迟 0.000823 墙钟秒；新 EGO 轨迹在 0.032 仿真秒后出现。
- PX4 经过 4.96 仿真秒首次进入停止带，保持 1.0 仿真秒；采样 51 次，最大间隔 0.024 秒。
- Gazebo 真值从取消到停止带的水平路径长度 1.304474 m，水平端点位移 1.030452 m；停止带内 1 秒真值最大水平变化 0.007558 m。真值最大源间隔 0.020 秒，共 250 个区间样本。
- 观测到的水平速度峰值 0.546083 m/s，PX4减速度p10为0.026538 m/s²，首次达到10%速度下降的时间为1.516仿真秒。这些是有限样本统计，不是保证下界。
- 定位健康策略旁路在状态中实际生效；normalized cost最高1.263780，大于原1.0对照值。此值仍被记录，但不再阻止该 N10 诊断动作。
- 禁止接触 0 次。独立 PX4／bridge 读回为 LANDED、landed=true、armed=false、control_enabled=false，控制样本为0；之后安全停止本轮容器。

## 解释范围

该样本只表示本次 #357 同配置路线、当前 Gazebo/PX4 SITL、0.500 m/s 触发状态下的取消响应。不能把 1.304 m 当作一般停车距离、最小走廊或速度保证。低速 #321 的 0.04014 m/s 取消样本停止路径为0.30407 m；跨速度样本只能用于校准对照，不足以拟合通用制动模型。

碰撞策略保持 `official_ego`，由上游 inflated-occupied 层判定规划碰撞；没有执行项目额外的 raw-free 整曲线拒绝门。Gazebo真值只用于离线评估，不是控制输入。净空由另一个静态SDF离线评估报告提供，不能由本报告的零接触替代。

## 原始产物

- 运行目录：`artifacts/runs/n10-20261026-359-high-speed-cancel-stop/`
- 量测：`n10-cancel-braking-evaluation.json`、`n10-cancel-speed-curve.csv`
- 独立复核：`debug-truth-evaluation.json`、`vehicle-contact-evaluation.json`、`postflight-px4-bridge-readback.json`、`safe-to-stop.json`
- 运行配置与身份：`n10-cancel-run-manifest.json`、`runtime-contract.json`
- 净空单独记录：`n10-clearance-evaluation.json`
- 机器可读轻量报告：[#359 JSON](n10-high-speed-cancel-stop-20261026-359.json)
