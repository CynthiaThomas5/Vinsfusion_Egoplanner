# N08.2ac #239：定位锁定时内部指标回读

## 范围

在同一 22 阶段、DISARMED 后向下视支架扫描中，只增加定位健康锁定时的一次性 Health.metrics 快照。目的为直接记录触发 normalized_cost_exceeded 的 telemetry 源戳和原始数值，并与同一 stamp 的 VINS telemetry 对照。门限、PX4 时间逻辑、话题与控制行为均不变。

Run：n08-20261024-239-health-lockout-readback-01

## 结果

- 支架扫描在第 16/22 段中止；下视姿态已到达。N05 before online/offline 同身份拒绝 TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope；没有 prescan-ready、post-release/current-area gate、compute-only、goal 或 XY。
- 新增快照恰好输出 1 次。Health.metrics.stamp_ns=506355999999，final_cost=2366.574815，residual_components=4690；按原公式得到 normalized_cost=1.004589641，超过原上限 1.0。
- 同戳 raw VINS telemetry 唯一一条记录的 final_cost 和 residual_components 完全相同，重算结果完全相同。该 run 的锁定有真实指标依据。
- 下一条 estimator telemetry 在 0.132 仿真秒后回到 cost=0.816258；状态机保持 fail-closed 锁定。不能因此忽略越线或放宽门限。
- cost 分组：visual 1236.373/4458 residuals；marginalization 1107.821/82；IMU 22.381/150。分组误差 2.27e-12，evaluation_ok=True。这量化了主要贡献，尚未单独证明上游根因。
- 4056 个 PX4 bridge 样本中，HRT 与 ROS /clock 差为 -8…16 ms；时间域无无效样本，bridge timestamp_error 为空，clock 回退 0 次。健康锁存后 adapter optimized/propagated 停在 506.224/506.356s，raw VINS/optimized/propagated 继续到 534.340/534.340/534.436s。最大 28.136s pair gap 是健康锁存后的下游后果。
- PX4 log 有两条 vehicle_imu duplicate timestamp 错误（487.132s）；bridge HRT/clock 读数仍有效。它们作为独立待查项记录，没有证据将其与该 cost lockout 建立因果。
- fixture 已 detach 并移除。fixture 末态 landed/disarmed；停止前 fresh CLI 读回 ARMING_STATE_DISARMED、landed=true、ground_contact=true、at_rest=true。project.sh stop 后容器 exited 0。

## 更正 #238

#238 原先以 LocalizationStatus.source_stamp 匹配 raw VINS telemetry。该字段由 adapter 设置为最近发布的 propagated odometry stamp，normalized_cost 则由最新 Health.metrics telemetry 计算；这不是相同指标时间戳的比较。#238 不能据此推断 false lockout。#239 将 Health.metrics.stamp_ns 与 raw telemetry 精确匹配后，final_cost、residual_components 和 normalized_cost 完全一致。#238 当次内部快照未保存，故当时的精确消息仍未知。#238 JSON、证据报告和对话摘要已补充此更正。

## 验证与产物

- 定向单测 56 项通过；固定容器 ROS 构建 17 包通过。
- project_status 结构检查通过，提示 80 个可选历史 artifact 链接缺失。
- 快照、最后安全读回、timeline 和原始运行日志位于 artifacts/runs/n08-20261024-239-health-lockout-readback-01/；各关键文件哈希见本报告 JSON。
- 父 N08 仍 in_progress。PX4 HRT/ROS clock 问题未复现；下一步是用单样本突增和视觉/marginalization分项选择下一项单变量动作，不提高 1.0 门限。
