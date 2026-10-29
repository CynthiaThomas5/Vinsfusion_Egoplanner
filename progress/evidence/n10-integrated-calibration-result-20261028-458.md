# N10.3/#458：max_cnt=220 正常综合校准结果

本次使用 #457 离线 VIO 指标通过的 `max_cnt=220` 候选，完成正常 16 m 导航、动态箱体重规划、20 仿真秒保持和正常降落。PX4/bridge 独立终态读回为 `LANDED`、disarmed、landed、control-disabled、zero-control；容器受控停止，未使用紧急 disarm。无故障注入，不计 N15/N16 正式次数。

**综合结论：`INSUFFICIENT`，N10.3/N10 保持未完成。** action、3.528 仿真秒独立位置/yaw 联合驻留、原 VIO 绝对误差/RPE10/速度草案、地图源/更新时效、同身份 raw/inflated 快照、覆盖范围内的表面/分类、sensor capture、接触和观察器身份绑定均通过。关键数值：目标段 raw VIO 位置 p95 0.08998 m，RPE10 平移 p95 0.040723 m，速度误差 p95 0.008398 m/s；保持速度误差 p95 0.002746 m/s；违规接触 0。

仍不足的出口：

- 物理步瞬时运动 observer 订阅成功但记录数为 **0**，所以全机连续区间净空为不足；采样物理状态最小净空 0.56104 m 仅是离散值，不能替代区间界。
- tracking p95 为 0.31494 m、最大值 0.32776 m；逐点平移下界样本均为正，但缺少由已测通道/包络推出的通用跟踪验收门限。
- 资源/队列没有按平台容量冻结的限值。观测到 cgroup 未限 CPU、无 OOM/throttling；mapper pending-depth 高水位到 8/8，并丢弃 depth 22、keyframe 21。VINS 队列为观测值，不代表容量。
- 动态障碍与替换样条均有记录，仍缺冻结的量化重规划依据；箱体的离线采样净空不能提升为连续安全证明。

observer 记录数为 0 的源码原因已定位：PX4 的 `px4-rc.gzsim` 以 `file://${PX4_GZ_MODELS}/${MODEL_NAME}/model.sdf` 直接选根 SDF。#458 虽生成了含插件的 run-local `x500_d435i` overlay 并加入 `GZ_SIM_RESOURCE_PATH`，但 `PX4_GZ_MODELS` 仍指向 `/workspace/simulation/models`，所以根 wrapper 插件没有进入实际模型。#459 修正这一路径选择并做无飞行启动验证；#458 原始归档保持不变。

详细原始记录位于 `artifacts/runs/n10-20261028-458-maxcnt220-integrated/`，结构化摘要见[JSON](n10-integrated-calibration-result-20261028-458.json)。主要输入包括 `flight.json`、`n10-acceptance-evaluation-458.json`、`n10-full-route-vio-segmented-metrics.json`、`n10-interval-clearance-bound.json`、`n10-tracking-clearance-relation.json`、`n10-resource-observation.json`、`n10-obstacle-replan-timing-analysis.json`、`n10-sensor-capture-evaluation.json`、`vehicle-contact-evaluation.json` 和 `safe-to-stop.json`。
