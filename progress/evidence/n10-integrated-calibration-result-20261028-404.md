# N10.3/#404 综合校准结果

## 结论

16 m EGO 目标动作成功，独立真值位置/yaw 联合达标窗口为 4.352 仿真秒；本次 15 仿真秒保持只是诊断。PX4 最终读回 `LANDED`、`armed=false`、控制关闭，零控制样本成立；安全读回后项目容器已停止。验收草案总状态仍为 `INSUFFICIENT`，本次不构成 N10 冻结或 N15/N16 正式次数。

原总 driver 返回码为 1，因为离线验收未整体满足。飞行记录显示 action `succeeded`；独立末态读回通过。末态 `reason` 字段仍保留最初 `DISABLED/px4_preflight_failed` 字符串，而 preflight 记录为通过、目标成功，稍后的落地转换原因是 `operator_disable`；不能把该历史字符串解释为本次末态由 preflight 失败导致。

## 主要测量

- **VIO**：目标段长 83.688 仿真秒；固定 scale-one 对齐后位置 P95/max `0.0721/0.0811 m`、绝对 yaw P95/max `0.258/0.268°`、速度误差 P95 `0.00821 m/s`。1/5/10 s RPE 平移 P95 为 `0.00908/0.02430/0.03856 m`，旋转 P95 为 `0.0709/0.3064/0.4203°`。均是单次校准观测，不是冻结阈值。
- **连续运动净空**：记录了 26,005 个连续 4 ms solver 状态。源码约束的 SITL 机体动力学界覆盖 25,187 个空气中无接触区间，最小区间净空下界 `0.16276 m`；817 个允许的滑橇/地面接触区间分开评估，独立接触记录有 14,399 个地面事件、0 个违规接触。该界只适用于当前模拟模型和无接触区间，不含定位/地图/跟踪误差，不能作为最终场景验收阈值。
- **跟踪预算**：9,381 个 READY 命令配对的跟踪误差 P95/max `0.3338/0.3422 m`。逐点“命令净空减位置误差”下界在 434/9,381 个样本为负；这是余量证明不足，不代表发生碰撞。几何关联的验收阈值仍未建立。
- **地图与重规划**：ROI cloud watermark 与快照同 map/epoch/frame，快照 source stamp 覆盖 watermark `0.960 s`。障碍实体内部中心分类为 unknown/free/occupied `1731/54/7`；八角均在实体内的体素中仍有 `18` 个 known-free，raw 分类候选判定为 `FAIL`。六面中仅负 X、负 Y 两面各有 20 个 raw occupied 支持；其余面的可见性/遮挡未建立。点查询服务 `/mapping/get_map_status` 不可用，独立点查询 `0/26`。Gazebo 创建 ACK 后 `0.188 s` 观察到首条替换样条，但单样本不能确定是障碍响应还是普通重规划，也不建立期限。
- **资源和采集**：资源观察覆盖 189.0 wall 秒/188 个采样点；RTF P50/P95 `0.894/0.916`，映射 pending-depth 队列高水位 8（配置容量 8），丢弃 depth/keyframe 各 21、转发 5,003，OOM 与 CPU throttle 观测为 0。VINS 内部队列容量未暴露，主机能力及代表性负载依据未建立，所以资源标准仍 `INSUFFICIENT`。只读 sensor capture 的 51,933 条收据与 bag 记录一致，三路流无时间戳回退、bag exit 0、无 evaluator 错误。

本次**未注入深度故障**：共享 `parameter_bridge` 同时承载多个图像流和 camera IMU，终止它不是深度单流中断。需先建立并验证隔离的深度中断路径，再测触发至自然 PX4 终态。本次未使用紧急 disarm。

验收器状态：到达、raw VIO、10 s RPE、速度、离线地图时效和全机净空/接触项有 PASS 观测；raw-map 分类为 FAIL；跟踪、跟踪净空预算、地图表面支持、动态重规划标准、故障终态标准、资源容量和 observer identity binding 仍为 `INSUFFICIENT`。不因这些离线结果增加起飞拒绝、取消或降落分支，也未恢复项目自加健康/经验速度/raw-known-free 门限。

## 复算与验证

- 修正离线 VIO evaluator 对当前 goal profile `position_tolerance_m` 字段的兼容，并把 15 s 分段从误导性的 `requested_600s_active_hold` 改名为 `diagnostic_post_goal_active_hold`；报告同时写明非正式 N16 qualification。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261028 python3 -m py_compile tools/debug_truth/evaluate_n10_full_route_vio_metrics.py tools/test_n10_full_route_vio_metrics.py`：通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261028 python3 -m unittest tools.test_n10_full_route_vio_metrics`：3 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-20261028 python3 tools/debug_truth/evaluate_n10_full_route_vio_metrics.py artifacts/runs/n10-20261028-404-speed040-integrated-calibration`：通过，已更新分段 JSON/log。
- `python3 tools/project_status.py`、`git diff --check` 与 JSON 校验：见本轮最终记录。

完整逐项结果和 19 个关键运行文件 SHA256 见 [JSON 证据](n10-integrated-calibration-result-20261028-404.json)。大文件保留在 [`#404 运行归档`](../../artifacts/runs/n10-20261028-404-speed040-integrated-calibration)。

## 下一步

N10 仍为 `in_progress`。先实现并验证只中断深度输入的路径，再按故障类补校准；继续收敛地图分类和跟踪净空依据、资源容量标准，随后完成 N10.4 验收配置、N10.5 隔离干净重建、N10.6 受影响回归及 N10.7 最终冻结。N15/N16 正式测试仍在冻结之后。
