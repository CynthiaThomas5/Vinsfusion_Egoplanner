# 当前状态

更新时间：2026-10-23。当前目标：[GOAL v3](../GOAL.md)；执行要求：[N01–N17](../docs/remaining-small-goals.md)；状态和证据登记：[milestones](milestones.json)。

## 已确认

**项目处于“已有仿真闭环与漂移研究，正在收敛独立质量和动作安全”的 P4–P6 阶段。** N01 已完成其限定范围的全状态 VIO 基线；其它小目标仍按里程碑状态推进，N01 不代表最终定位精度或飞行资格通过。

| 方面 | 当前事实 | 证据 |
| --- | --- | --- |
| 工程与固定场景 | P0–P3 历史通过；已有固定房间导航、异机重建与三连记录 | [#054](evidence/gpu4090-deployment-20261022-054.md) |
| 原始 VIO | N01 已通过：3 个 fresh epoch 完成位置／姿态／速度、1／5／10 秒 RPE、三次返回漂移和时序评估；旧 #057／#069 已按正确同点坐标更正。支持范围仅为低速、未武装支架仿真，不是精度门限或飞行资格 | [#083 证据报告](evidence/vio-full-state-baseline-20261022-083.md)、[#057](evidence/vio-drift-baseline-20261022-057.md)、[#069](evidence/odometry-drift-20261022-069.md) |
| 定位健康与时序 | N02 已通过：同一支持运动补测未复现 #02 质量代价越线；当前版本双目断流端到端触发 `left_stale` 锁存。#02 根因与 #04/#05 历史接收龄空窗原因未明，转入 N10 明确适用范围 | [#089 证据报告](evidence/n02-health-timing-20261022-089.md) |
| 深度实际融合 | N03 已通过限定的 idle 连续性出口：3 个独立 150 秒 fresh epoch 均满足 0.4 秒融合／源龄门，adapter 队列高水位为 3–4，steady `input_ready` 后 drop 计数增量为 0；当前版本 2 秒断流关闭门、reset ack、新身份融合重建，旧身份查询拒绝。一次冷启动 `telemetry_stale` 失败保留并转 N10 跟踪 | [#090 证据报告](evidence/n03-depth-fusion-continuity-20261022-090.md) |
| raw 地图几何与分类 | N04 已通过诊断测量出口：两布局各一个 fresh epoch、每轮三张同身份快照；表面、free／occupied／unknown、遮挡、inflation 和融合延迟均可复算。错误分类和通道第三张快照近一体素变化完整保留；这不等于完整 GOAL C 或飞行验收 | [N04 证据报告](evidence/n04-map-geometry-20261023.md)、[#091 进展](changes/2026-10-23-091-n04-map-geometry.md) |
| 回环研究 | 实际回环与优化有证据，位置误差降低；yaw 改善有限，单独增权产生位置回归；输出仍仅观察 | [#075](evidence/loop-drift-evaluation-20261022-075.md)、[#077](evidence/loop-yaw-weight-replay-20261022-077.md) |
| 在线安全实现 | 目标球、射线修复、完整曲线组件验证已有；当前整机飞行资格未取得 | [#062](evidence/goal-admission-20261022-062.md)、[#064](changes/2026-10-22-064-full-curve-admission.md) |
| 正式验收 | P4／P5／P6 进行中；A–H 仅 G 历史通过，最终需回归 | [最终条款](goal-checklist.json) |
| 本轮计划 | 新 GOAL、17 项执行书、状态依赖、旧版／旧 CURRENT 快照已整理 | [#080](changes/2026-10-22-080-goal-v3.md) |
| 默认推进规则 | “继续”后自动选定／恢复一个有界子任务；每轮预算、停止和交接规则已写入 AGENTS | [#081](changes/2026-10-22-081-agent-task-workflow.md) |
| Goal 模式补充 | 明确启动 Goal 任务时持续到指定目标完成，取消普通模式默认 30 分钟和两轮探索上限；仍服从真实阻塞、安全及用户／系统预算 | [#082](changes/2026-10-22-082-goal-completion-mode.md) |

## 证据推断

N03 已证实当前组合在静态未解锁 full idle 负载下的深度转发、EGO 同步接收、plan_env 实际融合与最近完成地图新鲜度连续；一次独立启动的 VINS telemetry_stale 被 fail-closed 捕获，仍由 N10 处理适用范围，不放宽健康门。N04 已在当前源码组合上交付两布局 raw 几何和分类测量，遮挡后 ROI 均保持 raw unknown；但通道地图存在预期 free 投票落入 occupied 和第三快照近一体素墙面移动，见证据报告。起降、全机包络和制动安全仍未验收。N01 的低速支架测量没有 roll 激励，pitch 仅约 0.28°；#065 一处 free 球和历史 16 m 成功均不足以推断当前全链可飞；回环收益也不直接构成接管依据。

## 待确认与 PROVISIONAL

- N01 #02 的 `normalized_cost=1.205982` 未在同一支持运动的 #085／#086 复现，触发时刻根因与是否属于真实估计退化仍未知；不能称误报或已修复。#04／#05 的状态／优化里程计接收龄空窗也没有单一归因。按 N02 出口要求转入 N10 冻结最终适用范围和所需回归。[#089 分析](evidence/n02-health-timing-20261022-089.md)、[#067 residual audit](evidence/vio-residual-audit-20261022-067.md)。
- 起点／起降／自身过滤、完整路径／停止和定位失效降落净空未验收；旧 4 m 返航目标仍禁用。当前 0.5 m/s、0.8 m/s²、0.5 m 膨胀、0.4 仿真秒地图超时均非正式安全认证。
- 优化／传播里程计仍以相机 IMU 为参考；实际机体安装、真实时间域、设备标定、机载满载与实机没有本仓库验收证据。
- 飞控／固件、机载电脑／系统、含桨尺寸、独立参考条件待补；实机 H0–H5 仅为[后续路线](../docs/simulation-to-hardware-roadmap.md)。

## 下一步

执行状态：Goal 完成模式；用户指定范围 N05。父目标 N05 依赖 N01、N04，当前为 in_progress。N05.1 几何／预算和 N05.2 raw-map 在线检查与归档回放已实现。wall r03、corridor r01 各完成旧 0.6 m profile 的 12 阶段扫描；before／attached-after 在线检查与离线回放一致，完整机体因 raw unknown 拒绝。wall r04 released 检查因当前 localization/map/bridge/odom/clock 状态不全而 fail closed，VIO 同期记有 `telemetry_stale`；corridor r02 因 VINS `normalized_cost_exceeded` 在 stage 10 中断，随后受控恢复将夹具回零、detach 并移除，独立复核确认 PX4 DISARMED、桥 DISABLED／landed 后才停止容器。高度假设已在 wall r05 验证：coverage profile 从 0.6 m 改为夹具许可的 1.0 m，路径／判据不变；完整 12 阶段后，hold 未知格由旧版 338 降至 163，但 TAKEOFF_CONTACT 仍有 498 个 unknown。释放后新鲜检查成功，same epoch/map_id、姿态变化 0.00047 m，在线／离线同为 unknown 拒绝，fixture 已移除，容器 exit 0。当前子项 N05.4：用同一 1.0 m profile 在 corridor 布局复核 full scan、VINS 稳定性、释放后准入及 map identity；不得放宽未知拒绝或误差预算。入口 `bash tools/run_n05_preflight_layout.sh RUN_ID LAYOUT`；仅 DISARMED 支架扫描与只读地图服务，不启用 Offboard、不发目标、不飞行、不连接实机。几何／误差预算仍为 PROVISIONAL。见 [#092 对话摘要](../collaboration/dialogues/2026-10-23-092-n05-preflight-entry.md) 和 [#092 改动记录](changes/2026-10-23-092-n05-preflight-entry.md)。

N04 的 sampled free-cell occupied 冲突、表面分类不完整以及通道快照 temporal shift 继续保留；这些诊断数据不能证明起降区域或全机净空。#065 的单个 0.5 m free 球不作为起飞准入。

N02 通过不代表 #02 的质量代价根因已知。该事件和 #04/#05 历史接收龄空窗必须在 N10 按最终运行范围决定保留条件及补充回归；不抬高 `normalized_cost` 门、不延迟锁存、不关闭故障保护。完整结论见 [#089 证据报告](evidence/n02-health-timing-20261022-089.md)和 [#084 过程记录](changes/2026-10-22-084-n02-health-timing.md)。

详细既有结论、失败及交付历史原样保留在 [重写前 CURRENT 快照](CURRENT.before-goal-v3-20261022.md)及 changes／evidence；快照为历史，不是第二个当前入口。未擅自提交或推送。
