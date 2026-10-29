# N06 全曲线布局与保持区审查

日期：2026-10-23。状态：**N06 进行中，出口未通过**。本报告属于 Goal 完成模式下的 N06 证据；不构成起飞、PX4 或飞行授权。

## 当前配置的两布局回读

最终使用 wall-r10 与 corridor-r10。每个 run 都有三份同 epoch、同 map_id、同 frame 的 raw occupancy 快照；source/fusion 年龄均小于 0.14 仿真秒，且 N05 body sphere 半径为 0.730617917 m、terminal hold 查询半径为 0.980617917 m。完整元数据和哈希见[机器可读报告](n06-full-curve-layout-review-20261023.json)及[回放产物](../../artifacts/runs/n06-map-sweep-20261023-r04/report.json)。

| 布局 | 实际 VINS 起点 body sphere | 起点 terminal hold neighborhood | exact hold 候选 |
| --- | --- | --- | ---: |
| wall-r10 | `unknown`，1,801 unknown / 410 free / 0 occupied | `unknown`，4,048 unknown / 804 free / 0 occupied | 0；已知 free-cell 最大中心距 0.781 m |
| corridor-r10 | `unknown`，1,807 unknown / 384 free / 0 occupied | `unknown`，4,085 unknown / 836 free / 0 occupied | 0；已知 free-cell 最大中心距 0.700 m |

`tools/analyze_n06_snapshot_sweep.py` 按生产闭格球查询与连续中点覆盖算术回放这两张真实快照。所有 snapshot identity/freshness 检查通过，但两个布局都没有可用的 N05 terminal hold 区，也没有离线曲线链。分析耗时分别约 0.975 ms 和 0.956 ms。

## live EGO 探测

wall-r10 的无控制 live probe 收到稳定 map identity，状态年龄为 source 0.106 s、fusion 0.018 s，ROS 图里没有 PX4／桥／controller／setpoint。body sphere 查询返回 `no_fresh_fused_depth`，EGO 生成 0 条曲线并报告 `full_curve_planning_failed`，迟到曲线数为 0，结果见[wall probe](../../artifacts/runs/n06-20261023-wall-r10/n06-live-layout-probe.json)。

corridor-r10 的三张快照已成功保存并通过离线 identity/freshness 检查，但 live probe 在 10 秒内没有收到 VINS odometry，因此未发送 goal；记录见[probe 日志](../../artifacts/runs/n06-20261023-corridor-r10/n06-live-layout-probe.log)。这不算 EGO 曲线验证。

此前配对的 wall-r07／corridor-r08 motion_n06 run 使用 map-bottom=-0.8 m。其 live EGO 同样未产生曲线、两次均为 `full_curve_planning_failed`。wall-r07 的离线搜索曾找到一个 0.601 m 两段候选链，但其起点远离实际 VINS 起点，且扩大到紧急保持包络后第 12 个采样查询遇到 1 个 unknown；corridor-r08 没有 hold 候选。它们仅用于诊断，不能替代当前配置或 live EGO 证据，细节见[旧版双布局回放](../../artifacts/runs/n06-map-sweep-20261023-r03/report.json)。

## 保持区边界修正

实际 terminal hold query 半径是 body radius + 0.25 m，即 0.980617917 m；原 map bottom=-0.8 m 会使 z≈0 的 hold 球先被拒为 `outside_map`。现已将 planner ground height 与 policy required map bottom 调整到 -1.0 m，并在 resolver 中要求地图边界覆盖完整 body sphere 加 hold neighborhood。unknown 仍拒绝，没有做未知转 free。wall-r10／corridor-r10 的离线回读已确认查询进入地图后仍返回 `unknown`，因此修正没有消除真实覆盖缺口。

## 合成组件回归

合成 EGO 组件 probe 的活动曲线证书为 61 次查询、0.528 ms；wrong map_id 被拒，unknown 与 planning failure fail-closed，故障后迟到曲线为 0。after-completion probe 也通过：61 次查询的端点曲线在 hold 扩张区发现 obstacle，返回 `full_curve_terminal_hold_occupied`，无迟到曲线。两份结果分别为[活动曲线报告](../../artifacts/runs/flight-safety-20261023-093-component/result.json)与[terminal hold 报告](../../artifacts/runs/flight-safety-20261023-093-component-terminal-hold/result.json)。这些是合成组件证据，不替代两布局 live EGO。

高角度观察扫描的单次假设实验 wall-r09 在 snapshot-02 等待时触发 mapping input freshness gate 关闭；已通过 runner SIGINT 清理，并确认项目容器和进程停止。该 run 没有产生可用的第二、三张快照，不能用于覆盖结论。

## 验证与状态

- `bash tools/project.sh build ros`：17 个 ROS 包通过。
- `bash tools/project.sh test`：243 项通过；navigation adapter 集成检查通过。
- `python3 tools/analyze_n06_snapshot_sweep.py --run-id n06-20261023-wall-r10 --run-id n06-20261023-corridor-r10 --output artifacts/runs/n06-map-sweep-20261023-r04/report.json`：完成；两布局快照有效，但没有 hold 候选或 offline chain。
- Python 编译、motion profile 形状检查、`bash -n tools/run_n04_map_layout.sh tools/run_n04_map_layout_container.sh` 与 `git diff --check`：通过。
- 没有启动 PX4、bridge、trajectory server、controller 或飞行任务。

## #095 追加：N06.3 视场归因与 N06.4 下一动作

wall-r10／corridor-r10 的 snapshot-03 body 球与 terminal-hold raw query 数已由独立脚本复算。对应 unknown cell center 在精确 source 相机位姿及采集至 source stamp 的全部 692／697 个相机位姿中，均未投影到几何成像区域；详细闭格查询数与后方／近裁剪／出画分类见[N06.3 报告](n06-observation-coverage-diagnostics-20261023-095.md)。这支持观测覆盖不足，但不判定深度射线、遮挡或 occupancy 分类是否正确。

wall-r10 的 fresh map 状态与单次 `no_fresh_fused_depth` query 并存；pending-pair 语义是有 N03 先例支持的解释，r10 未记录请求时 pending 标志。corridor probe 的 fresh odometry timeout 与 sim 39.597 s 后 `normalized_cost_exceeded` 持续无效相符。N06.3 诊断完成；下一项改为 **N06.4 r21 四分之一 yaw-rate 复核**，不改变 N06/S4 `in_progress` 状态或验收条件。

N06 尚缺两布局中可从实际 VINS 起点连续扫掠的全机 EGO 曲线、terminal/emergency hold 和 replan handoff。因此 N06 保持 `in_progress`，`next_goal` 保持 N06。完整 N06.3/下一动作摘要见[N06.3 证据报告](n06-observation-coverage-diagnostics-20261023-095.md)。

## #096 追加：r21 慢速 yaw 结果

r21 相比 r20 把峰值 yaw 角速度降至四分之一后，VINS 估计姿态在 sim 45.574 s／yaw 16.37°触发 `normalized_cost_exceeded`，晚于 r20 的 sim 13.564 s／yaw 2.43°，但仍未支撑 full turn。15 秒容器停止宽限用尽后，run 以 exit137 结束；mapping stack log 留存，motion truth 与 recorder inputs 未落盘，故姿态证据只有 VINS 估计值。N06.4 下一假设改为同速 15° rest-to-rest yaw 步进及逐步静置 5 秒；details 见[慢速 yaw 诊断](n06-observation-scan-diagnostic-20261023-096.md)。host cleanup 已加长到 90 秒，r22 将通过容器内 SIGINT motion 进程组触发有序 partial-record cleanup。

## #097 追加：r22 15°停顿未跨过早期健康门槛

r22 的首次 map health lock 在 sim 12.970 s／估计 yaw 2.41°，debug fixture truth 约2.63°；首个15° rest-to-rest hold 要到 sim20.117 s。健康门槛关闭后，feature counts 在部分后续 hold 间歇增加，但所有已录 localization status 持续无效、MapStatus不恢复。360°命令在 motion truth 中只达到约337.75°，因此也未完整覆盖一圈。input recorder完成428秒窗口，但EGO-forwarded depth/pose只记录263帧，health lock后没有持续有效map输入；snapshot readiness wait超时，没有snapshot或EGO目标。原始数据及停顿窗口复算见[分段重获报告](n06-observation-scan-reacquisition-20261023-097.md)。

runner中断处理已加入显式signal handlers，并将host stop grace设为90秒。当前N06.4下一步为r23八个1° rest-to-rest yaw pilot，每步静置约5.16秒；它只检验早期定位健康，不代表N06通过。


## #098 追加：r23 1°微步结果与 r24 下一动作

r23 的首个1°步进之后，静态hold后段VINS `n_pts` 回升至约111–113；第二步开始后特征降至个位数，sim18.844s／估计yaw1.961°时mapping health gate关闭，sim18.910s第一条LocalizationStatus变为invalid，原因`normalized_cost_exceeded`，当时debug truth yaw约1.546°。MapStatus随后变为`map_reset_acknowledged`并保持未ready；没有snapshot输出。该结果表明静止暂停可带来局部feature reacquisition，但1°步长仍不能维持健康跨越失效点。记录、样本哈希及truth计算见[r23证据](n06-yaw-microstep-reacquisition-20261023-098.md)。

唯一下一子项仍为N06.4：r24将最大不间断角度降到0.25°，保持角加速度、每次5.164秒hold和wall场景，以8步／2°pilot验证能否越过r23约1.55°truth-yaw失效点。profile尚待运行，N06/S4仍为`in_progress`。


## #099 追加：r24 0.25°步进未维持定位健康

r24将最大不间断角度降到0.25°，但在truth yaw约1.199°（sim29.668s）仍触发`normalized_cost_exceeded`；首条invalid status在sim29.751s／truth yaw约1.209°。三个hold的VINS特征计数中位数约109、112、114，IMU积分yaw与truth仅差约0.00008°，而VINS估计yaw约2.310°。MapStatus随后保持`map_reset_acknowledged`，120秒readiness wait未生成snapshot，runner exit1并清理容器。详见[r24证据](n06-yaw-microstep-reacquisition-20261023-099.md)。

下一项仍为N06.4：r25保持0.25°步进、2°nominal total、每步5.164秒hold与场景，只把角加速度降四倍至0.0026179939 rad/s²，检查运动瞬态是否与VINS/truth估计偏离及health lock相关。profile尚待运行；N06/S4和原验收阈值不变。


## #100 追加：r25 四分之一角加速度仍触发健康锁存

r25保留0.25°步进、2°命令总角和每步约5.164秒静止hold，仅把角加速度降四倍。health gate仍在sim33.958s／truth yaw约0.927°关闭，首条invalid status在sim34.060s／truth yaw约0.938°。锁存LocalizationStatus的normalized cost为1.04236，超过未更改上限1.0；IMU积分与debug truth相符，VINS估计yaw偏高约0.705°。MapStatus保持`map_reset_acknowledged`，120秒snapshot readiness timeout无输出。运行详情见[r25报告](n06-yaw-motion-transient-20261023-100.md)。

下一项为r26连续低速2°pilot：保持角加速度、peak rate、名义总角与场景，只将重复rest-to-rest停启改成一次加速、匀速巡航、减速。Goal和S4保持`in_progress`。


## #101 追加：r26连续2° yaw 保持健康，但body仍unknown

r26的motion truth实际累计2.0116°。Input recorder期间899条LocalizationStatus全部有效，MapStatus一直ready。三张snapshot共用epoch、map_id和frame，source age分别0.152／0.102／0.138秒；错epoch和错map_id拒绝检查通过。现场VINS body球query仍为1,809 unknown、397 free、0 occupied。无控制EGO probe身份和freshness稳定，goal因`full_curve_planning_failed`被拒，0条曲线和0条迟到曲线。完整细节见[连续yaw报告](n06-continuous-yaw-observation-20261023-101.md)。

下一项r27只把连续scan从2°扩展到15°，维持r26低角加速度和单次accel／cruise／decel；检验健康能否保持并测量body／hold覆盖变化。N06与S4保持`in_progress`，N06原验收标准不变。

## #102 追加：r27 连续15° yaw 未达到健康／快照门槛

r27 truth实际累计14.731°，但mapping health gate在sim62.404s以`normalized_cost_exceeded`关闭；VINS `n_pts=2`、估计yaw约10.161°，在线锁存normalized cost为1.34155。首条invalid LocalizationStatus为sim62.478s／truth yaw约9.854°。MapStatus在sim62.569s换map identity并关闭为`map_reset_acknowledged`，之后未恢复；150秒输入记录有1,762 depth/camera-pose pairs和881 optimized odometry，但最新已转发相机位姿source stamp停在sim62.338s。snapshot readiness等待120秒后超时，无snapshot／live EGO。详见[#102证据](n06-continuous-yaw-15deg-observation-20261023-102.md)及[运行目录](../../artifacts/runs/n06-20261023-wall-r27/)。

下一项改为 **N06.5 r28单轴平移观察**：在同一wall布局与N06纹理surround运行已有慢速X profile，sensor-only后退2.4m再返回起点、无yaw／Y／Z，验证平移视差能否维持定位并从原点后方观察原点body球。r14／r16使用同profile但没有surround且以`input_features_insufficient`锁存；r28用于在已增加纹理环境下复核。命令：

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r28 wall_box_column 91 motion_n06 config/components/simulation/n06_x_visibility_slow.json
```

通过r28健康／MapStatus freshness后才保存三张快照和运行planner-only probe；N06/S4仍`in_progress`，`next_goal=N06`，原全机连续扫掠、hold、handoff、双布局与拒绝出口不变。

## #103 追加：r28 单轴平移取得 wall body／hold raw free

r28沿单轴X后退2.3945m并返回，truth yaw全程0°；2,019条LocalizationStatus全部有效，444条MapStatus同identity ready。三张fresh snapshot source/fusion age分别为0.116／0.039s、0.099／0.042s、0.145／0.041s。以live probe当时VINS位置复算，三张snapshot的body球均为2,195 free／0 unknown／0 occupied，terminal-hold球均为4,923 free／0 unknown／0 occupied；错误identity拒绝通过。这是一个wall布局、未武装观察流程的正向raw入口结果。机器细目及哈希见[#103](n06-translation-entry-pilot-20261023-103.md)、[机器报告](n06-translation-entry-pilot-20261023-103.json)和[raw回放](../../artifacts/runs/n06-20261023-wall-r28/n06-body-hold-replay.json)。

live body sphere服务一次返回`no_fresh_fused_depth`。runner内置goal`(+0.5,0,+0.5)m`的live EGO证书在terminal hold遇到5个occupied cell而fail-closed；offline exact query证实目标扫掠段free但hold不free，故这是正确的目标拒绝，0条曲线／0条迟到曲线，控制free graph通过。`(0,+0.6,0)m` lateral目标在相同快照的hold球与直线body sweep均free；下一项是 **N06.6 r29 live lateral-goal probe**，重建同一fresh scan map并只改目标offset，要求实际EGO产出goal匹配的完整B-spline证书。执行协议见[#103](n06-translation-entry-pilot-20261023-103.md)。N06/S4仍`in_progress`，原两布局、hold、handoff与故障出口不变。

## #104 追加：r29 wall-layout 实际EGO lateral 曲线通过

r29在wall layout复用单轴X后退／回程观察profile。2,015条LocalizationStatus全有效，MapStatus维持一个ready identity；三张snapshot source/fusion age为0.113–0.144／0.045–0.048s。以实际probe VINS pose复算，三张map的body球均2,219 free／0 unknown／0 occupied，hold球均4,862 free／0 unknown／0 occupied。自定义目标`(0,+0.6,0)m`在同快照直线body sweep与terminal hold均free。

probe在snapshot-01后、snapshot-02前提交目标；真实EGO发布了匹配goal_id和epoch的order-3 B-spline，full-curve证书`reason=free`、45次query／0.430ms，fault和fault后迟到曲线均0，identity稳定。控制free graph没有PX4／bridge／controller／traj_server／setpoint或control topic。起点body service的一次query仍为`no_fresh_fused_depth`；planner完整曲线证书和三张raw快照均通过，保留该差异。runner默认目标`(+0.5,0,+0.5)m`仍以`full_curve_terminal_hold_occupied`拒绝，和预期的occupied hold raw voxel一致。详见[#104证据](n06-live-ego-lateral-curve-20261023-104.md)、[机器报告](n06-live-ego-lateral-curve-20261023-104.json)与[运行目录](../../artifacts/runs/n06-20261023-wall-r29/)。

下一子项为 **N06.7 r30 corridor layout live curve**：在`corridor_box_column`复用X观察流程，取得匹配fresh snapshot后精确查询起点body、后方terminal hold和全段body sweep；走廊内宽约1.5m小于0.981m hold直径，若后退到走廊外的候选区全部raw free才提交planner-only目标，否则不发goal并保留fail-closed证据。N06/S4及`next_goal=N06`不变；两布局、hold／handoff、fault matrix全部出口仍需通过。

```bash
bash tools/run_n04_map_layout.sh n06-20261023-corridor-r30 corridor_box_column 93 motion_n06 config/components/simulation/n06_x_visibility_slow.json
```
