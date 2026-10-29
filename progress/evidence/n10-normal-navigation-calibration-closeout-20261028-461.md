# N10.3/#461 正常导航校准收口（#460）

## 结论与范围

按 #459 修正后的 PX4 run-local 根 SDF 来源，#460 完成一轮正常 16 m 目标、动态箱体重规划、20 仿真秒 hold、正常降落和独立安全读回。该运行不是故障测试，也不计入 N11–N16 正式次数。N10.3 的正常导航校准指标已具备当前候选版本的单次综合量测；验收配置继续为 draft，N10 尚未冻结。

运行：`n10-20261028-460-maxcnt220-kinematics-integrated`。runtime contract SHA-256 `a956bdb68779306c6786db8e6e7a694eb42cf6217613e757a5452e04b4d82b3d`，goal `163839f854ce40409885632884291319`，epoch `055de95a11dc4f7bb520f0d9f8f227ba`，map `055de95a11dc4f7bb520f0d9f8f227ba-a4e1e8a76ca04ed086e323a06e8ad39c`。PX4 使用的模型 SDF 路径、SHA 与 run-local contact overlay 一致；模型运动插件身份由离线报告绑定，不参与任务准入或控制。

配置 [acceptance.json](../../config/acceptance.json) 更新为 revision 8，只补证据引用和物理步校准状态；数值、比较符、任务行为和 `runtime_effect` 均未改变。13 项当前范围内的必需指标为 PASS；被用户 #434 排除的 fault-exit 项仍为 `INSUFFICIENT` 且 `required=false`。整份报告仍为 `INSUFFICIENT`，因为配置是 draft，不能当作冻结标准或正式资格。

## 量测结果

| 指标 | #460 结果 | 当前草案解释 |
| --- | --- | --- |
| 位置/yaw 联合到达 | 连续 3.596 sim s；窗口最大位置误差 0.29948 m、最大 yaw 0.18377 rad；native action 成功 | 达到 GOAL F 的 0.30 m、15°、3.0 sim s 原值 |
| Raw VIO 绝对误差 | 运动位置 P95/max 0.12118/0.12951 m，yaw P95/max 1.1065/1.1685°；20 sim s hold 位置 P95/max 0.10095/0.10136 m，yaw P95/max 1.3253/1.3309° | 单次当前 `max_cnt=220` 飞行量测；候选限值仍待 N10.7 冻结 |
| Raw VIO 10 s RPE | 运动平移/旋转 P95 0.04221 m/0.16219°；hold 0.00447 m/0.09349° | 分段均单独计算；full-task RPE 不替代运动和 hold |
| Raw VIO 速度误差 | 运动 P95/max 0.01033/0.01699 m/s；hold P95/max 0.00137/0.00255 m/s | 只读量测；不构成速度控制或起飞门 |
| 地图时效 | source age 最大 0.164 sim s；occupancy update age 最大 0.100 sim s | 均在离线 0.20 s 草案值内；没有恢复项目自加时效门 |
| 地图表面与分类 | 身份绑定 snapshot 上 5 个可观察面最大中心误差 0.07131 m；`x_positive` 未观测。完全被实体遮挡的 known-free cell 数为 0（unknown 1792） | 仅支持已观测表面及该遮挡 ROI；不宣称六面齐全或普适分类错误率 |
| 跟踪与实际净空 | 14,381/14,381 条 READY 命令与真值配对；最大真值括区 4 ms；跟踪误差 P95/max 0.31967/0.33522 m；最小实测全机分量净空 0.11002 m | 直接按同一时刻姿态与 SDF 碰撞组件几何判定；仅跟踪误差标量的平移 Lipschitz 下界有 1,119/14,381 个负样本，保留为诊断，不解释成碰撞 |
| 全机连续区间净空 | 30,664 个求解状态；30,663 区间完整分段；无接触空气区间最小模型下界 0.10309 m；最大间隔 4 ms；禁止接触 0 | 超过 0.10 m 草案值约 3.1 mm；这是指定 Gazebo/X500 模型范围内的动力学有界结论，不是实机保证；滑橇接触另行分段 |
| 动态重规划 | 首个正向 EGO occupancy cloud 在注入后 6.596 sim s（ROI 12 点）；旧轨迹预测净空边界还剩 14.818 s；2.972 s 后出现满足 0.10 m 机体 margin 的替换轨迹，margin 0.31496 m；首个 READY 源时间比边界早 11.846 s；之后 582 条 margin 合格样条，最小 margin 0.25202 m；替换后的 11,188 条 READY 均配对，实际净空下界 0.11002 m，禁止接触 0 | 用事件与旧样条的几何边界定期限；固定 1.0 s 延迟候选仅为诊断，本次不满足该候选，未作为验收门 |
| 资源与队列 | 295 个样本，约 298.31 wall s；最大采样间隔 1.1445 s；最大 CPU 15.81/32 physical-core-equivalent；cgroup 峰值内存 3.741 GB/主机总内存 66.88 GB；CPU throttling/OOM 增量为 0；mapping pending 最大 7/8，队列 high-water 8/8，depth/keyframe drop 22/21；VINS 队列当前深度趋势 0，容量仍未知 | 是一次代表性负载校准，不抵扣 N16 600 sim s。内存比较基于总 RAM 而非每时刻 free RAM；VINS 容量不由观测 high-water 推断 |

任务最终 `LANDED/disarmed/control-disabled/zero-control` 读回通过。#460 原始输入没有被重写；本报告的区间净空评估保存在 `artifacts/reanalysis/n10-20261028-460-component-geometry/`。评估器为取得该外部重分析输入使用 run 的隔离副本，并将同身份 interval report 放入副本；对原始归档执行评估时若漏掉此输入，判断器会给出 `INSUFFICIENT`，不能把缺失输入解释成飞行失败或通过。

## 版本比较与可复用范围

- #438 对 #381/#385/#436 使用统一的 model-origin→IMU 参考、固定 PRESTREAM 锚点和分段定义，但明确不跨 runtime 拼接数值。#381/#385 的 VINS 配置 SHA 为 `c4b49f…`，X500 模型 SHA 为 `1e2598…`；#460 的 VINS 配置 SHA 为 `923bd1…`，X500 模型 SHA 为 `d129da…`。旧记录保留为独立历史结果，不作为 #460 的同版本重复次数。
- #436 与 #460 的 runtime 中 VINS 配置、vehicle-envelope 和安装产物不同；cross-run pair 的状态仍是 `INSUFFICIENT`。本报告只采用 #460 自身飞行记录、输入身份及对 #460 的离线重算。
- #457 对同一完整 native 输入回放、`max_cnt=220` 仅 VINS 离线候选，RPE10 P95 为 0.048997 m、hold 速度 P95 为 0.006268 m/s；最高解算样本 40.947 ms 略高于其 40 ms 目标。#460 提供当前候选的一次完整 SITL 量测，但它不升级为重复性或正式资格。
- #399/#407 先前 raw-map 分类 FAIL 保留。#460 当前身份 snapshot 的遮挡 cell 检查为 0，只支持本次 ROI；不可追溯地删除旧失败，也不扩大到未观察的面。

## 判断器复放与验证

离线结果：`artifacts/reanalysis/n10-20261028-460-component-geometry/n10-acceptance-evaluation.json`。其 SHA-256 为 `6a45f7e16a7dda6a1b579d408e6455f84534ecb5c3ab00e6dabe86168a8722c9`；使用 acceptance revision 8，配置 SHA-256 `9a49da186d970ed9a49eb0fb4fa28b5b23cad9c17198a9563d7d63b0cea3ce63`。区间、跟踪、重规划和平台容量报告分别按相同 run/goal/epoch/map identity 绑定。

复现命令（`RUN_SCRATCH` 是原始 run 的工作区外副本，原始 `artifacts/runs` 不写入重分析报告）：

```bash
python3 tools/debug_truth/evaluate_n10_acceptance.py \
  --config config/acceptance.json \
  --calibration-report "$RUN_SCRATCH/n10-cross-run-calibration-with-436.json" \
  --run-dir "$RUN_SCRATCH" \
  --run-id n10-20261028-460-maxcnt220-kinematics-integrated \
  --tracking-clearance-report artifacts/reanalysis/n10-20261028-460-component-geometry/n10-tracking-clearance-relation-v3.json \
  --dynamic-replan-report artifacts/reanalysis/n10-20261028-460-component-geometry/n10-obstacle-replan-timing-analysis-v3.json \
  --platform-capacity-report artifacts/reanalysis/n10-20261028-460-component-geometry/n10-platform-capacity.json \
  --snapshot-report "$RUN_SCRATCH/n10-box-map-snapshot-analysis.json" \
  --output artifacts/reanalysis/n10-20261028-460-component-geometry/n10-acceptance-evaluation.json
```

对离线评估器、物理步区间、跟踪几何和重规划几何的定向回归：

```bash
PYTHONPYCACHEPREFIX=/tmp/n10-pycache python3 -m py_compile \
  tools/debug_truth/evaluate_n10_acceptance.py \
  tools/debug_truth/evaluate_n10_replan_geometry.py \
  tools/debug_truth/evaluate_n10_tracking_clearance.py \
  tools/test_n10_acceptance.py tools/test_n10_replan_reference.py
PYTHONPYCACHEPREFIX=/tmp/n10-pycache python3 -m unittest \
  tools.test_n10_acceptance tools.test_n10_interval_clearance_bound \
  tools.test_n10_tracking_clearance tools.test_n10_replan_reference -v
```

结果：编译检查通过，51 项测试通过。没有改运行源码、planner、VINS 参数、地图规则或验收数值；没有新增运行拒绝、取消、暂停、降落分支。N10.4 草案及离线判断器可复放，正式冻结身份留到 N10.7。
