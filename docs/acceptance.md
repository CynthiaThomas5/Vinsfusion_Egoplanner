# 阶段与验收

最终硬性回收标准以 [GOAL.md](../GOAL.md) 的 A–H 为准。本文件为阶段导航；其中原有“建议次数”已由 Goal 固定为正式验收要求。定量阈值须先冻结，再正式测试。

| 阶段 | 内容 | 必需证据 |
| --- | --- | --- |
| P0 | 旧工程差异、依赖及修复冻结 | 源码与 binary 对应、依赖 commit、补丁顺序、接口基线 |
| P1 | D435i 等效传感器 | 双目配对、IMU 单位及重力、深度平面、K／TF／clock 检查 |
| P2 | Jazzy VINS 与地图输入健康 | 实际编译、受控运动、无尺度拟合轨迹评估、深度源时间位姿对齐、失效门与 epoch reset 回放 |
| P3 | 真值调试闭环 | 在线深度地图、EGO、起飞绕障到达降落；明确 truth profile |
| P4 | VINS 地图与规划 | 深度时刻位姿、外参、墙面重影、延迟和地图更新报告 |
| P5 | 无 GPS 视觉闭环 | EKF 外部视觉实际融合、无真值位置辅助、规划与飞控坐标对齐 |
| P6 | 完整项目验收 | 多场景／冷启动／故障结果、地图快照、运行说明及可重建版本 |

当前骨架检查不算 P0 通过。milestones.json 的状态可为 not_started、in_progress、passed；passed 必须链接 progress/evidence 下实际报告，报告再引用原始 run。

最终任务：冷启动 → VINS 就绪 → 起飞 → 三维目标及 yaw → 在线建图／绕障 → 到达反馈 → 降落 → 地图与指标归档。

正常场景包含空场、单障碍、多障碍、满足膨胀条件的窄道、不可达目标；故障包含双目／IMU／深度断流、定位重启、规划器退出和时钟重置。建议正常场景各三次冷启动、连续运行至少十分钟，阈值在基线测量后正式验收前冻结。

记录碰撞接触、最小机体间距、任务成功率、到达与跟踪误差、定位误差、重规划及端到端延迟、CPU／内存曲线。真值只供离线评估；不能把屏幕路径看起来合理视为碰撞或精度验收。

## 实施顺序与最终验收的关系

当前按 [GOAL v2](../GOAL.md) 的 S1–S6 推进；S1–S4 是稳定性与安全诊断出口，S5 先冻结标准，S6 再开展正式 D／E 与全部 A–H 验收。旧 P0–P6 状态与已有证据保留，不因替换目标自动升级。步骤跟踪在 [milestones.json](../progress/milestones.json)。

## VIO 飞行诊断

需要在受控诊断 run 中分析 VIO 轨迹时，可单独启动 `config/components/simulation/debug_truth_bridge.yaml`，并让只读记录器订阅真值；VINS、建图、导航和 PX4 节点仍使用 `vio_closed_loop` 配置且不得订阅真值。此观察器只用于离线误差分析，该组合不属于最终无真值验收。

记录器有意要求显式传入诊断话题：

```bash
python3 tools/probe_vins.py \
  --session artifacts/runs/<stack_run_id>/session/session.json \
  --output artifacts/runs/<run_id>/vio-truth-capture \
  --seconds 90 \
  --truth-topic /debug_truth/base_odometry \
  --imu-topic /sensors/d435i/imu
```

飞行探针写出报告后，可按该报告时间窗对齐 raw VINS 与真值轨迹，并关联 quality telemetry：

```bash
python3 tools/evaluate_vio_quality_alignment.py \
  --capture artifacts/runs/<run_id>/vio-truth-capture \
  --flight-report artifacts/runs/<run_id>/vio-ego-flight-report.json \
  --output artifacts/runs/<run_id>/vio-truth-capture/vio-quality-error-evaluation.json
```

评估使用一次固定 SE(3) 对齐，不拟合尺度、不分段重对齐；单次相关性不能冻结验收阈值或替代多轮正式验收。

前向单相机首版限制盲区运动并配套 yaw 观察策略；unknown 不直接当 free。最大速度与制动距离按延迟和实测减速度约束。地图／轨迹过期但定位有效时受控制动，定位无效时退出自主导航并按固定 PX4 策略处理。
