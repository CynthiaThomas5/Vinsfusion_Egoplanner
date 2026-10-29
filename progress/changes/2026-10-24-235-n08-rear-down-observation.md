# N08.2y #235：后向下视补充 N05 起降体素观察

## 问题与假设

#234 的同图只读 audit 将 TAKEOFF_CONTACT 的 33 个 unknown cell centers 定位到已确认 ground plane 上方的薄层，HOLD 则 0 unknown。它们集中在起始机体后向（yaw=−π 时朝向）且靠近地面的区域。假设是在保持水平后向观察之外，于 yaw=−π 加一次 pitch=+0.45 rad 下视深度观察，可以使相同 N05 规则下的起降包络获得所需观测。

## 唯一变量、范围与产物

- 唯一主要变量：在 #234 的 yaw=−π 视角增加 pitch=+0.45 rad 的停留，再返回 pitch=0 后按原路线回中；其余 #234 既有阶段顺序、世界、释放／生成位姿、地图、目标、planner、N05／定位门限不变。
- 新 profile：`n08_overhead_rear_down_view`，22 stages。新增 profile config、runner allowlist 和 profile 单测。
- 允许运行：DISARMED N05 physical-support scan；只有 fresh post-release/current-area N05 online/offline admission 同 identity 通过后，才运行原有 bridge-isolated compute-only。compute-only 仅用于 READY／取消／保持与同图几何诊断。
- 禁止本子项执行 XY、改变 unknown/N05/N06/速度/PX4 阈值、或启动实际执行模式。若 N05 admission 拒绝，不发送 navigation goal。

## 判据与交付

- 静态：profile 22/22 stage 定义有效；其前 13 stages 与 #234 相同，新增后向 pitch 阶段并恢复水平 pitch 后才开始 yaw 回程；配置、shell、Python 语法和项目结构检查通过。
- 运行：确认阶段完成、fixture detach/remove、最终 landed/disarmed；post-release/current-area online/offline gate 同 epoch/map 且一致。拒绝仍按真实 unknown 报告；不以 helper 摘要覆盖安全读回。
- 若 gate 通过，保存 same-identity map／曲线与 compute-only 结果；不得把 compute-only 当作执行或制动证据。

对话摘要：[dialogue](../../collaboration/dialogues/2026-10-24-235-n08-rear-down-observation.md)。


## 结果与限制

- Run `n08-20261024-235-rear-down-observation-01` 初始 N05 before online/offline gate 同 identity 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。
- 22-stage scan 仅完成前 4 stages，在 yaw≈0、初始远移后的 pitch 调整阶段因 `normalized_cost_exceeded=1.401698` abort；新增 yaw=−π/pitch=+0.45 后向下视未到达。最后一条 trace 仍 valid/cost 0.5765，具体 health transition 未捕获。无 `n05-prescan-ready`，没有 after/post-release gate、compute-only、goal、控制、XY 或制动测量。
- VINS/odometry 只读时间线：VINS telemetry 最大 source gap 0.66 s，raw odometry 最大 gap 0.724 s；adapter optimized odometry 的最后 source stamp 约193.912 s，raw 源最后约241.696 s。该长空窗可能是在健康失效后停止输出；录制数据未确定因果先后。PX4 日志有重复 IMU sample timestamp 错误，但本 run 没有飞行时间门验收，不能把失败归到 PX4 HRT 修复。
- 扫描停滞时项目容器 CPU 约582%、Gazebo 321%、VINS 92%；宿主机有两个非项目高CPU模拟器进程，可能是资源压力来源但因果未证明。没有触碰这些进程。
- 末态 fixture detached、模型 absent、landed；PX4 bridge `DISABLED/localization_not_tracking`、`armed=false`、`landed=true`。项目 stop exit0，container Exited(0)，无活动项目进程；helper exit1、wrapper exit12。
- Evidence：[报告](../evidence/n08-rear-down-observation-20261024-235.md)、[JSON](../evidence/n08-rear-down-observation-20261024-235.json)。完整诊断记录：[dialogue](../../collaboration/dialogues/2026-10-24-235-n08-rear-down-observation.md)。

本次对后向下视地图覆盖假设没有判别力，不能算 N08 通过或否定。下一步在仿真时间推进稳定、共享CPU负载不再压制此运行时再重试同一profile；加只读状态时间线，捕获 normalized-cost 转换和 optimized-odometry 停顿。健康、N05 和 unknown 门限保持不变。
