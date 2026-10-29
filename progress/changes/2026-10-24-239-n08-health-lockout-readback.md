# N08.2ac #239：定位健康锁定指标快照

## 改动

- Health 新增只读 diagnostic_snapshot，含锁定原因、normalized_cost、由原始指标重算的 cost、门限、telemetry 与各流样本时间。
- Localization 在每个 epoch 首次 fail-closed 锁定时输出一条 health_lockout_snapshot JSON 日志；不改变门限、状态机、话题或控制。
- 增加定位健康快照单测。

## 验证与运行

- 定向 unittest：56 项通过。
- bash tools/project.sh build ros：17 个 ROS 包通过。
- python3 tools/project_status.py：结构检查通过；提示 80 个可选历史 artifact 链接缺失。
- DISARMED run n08-20261024-239-health-lockout-readback-01 在 16/22 stage 锁存。Health.metrics stamp 与同戳 raw telemetry 一致，normalized cost=1.004590。HRT/clock 差 −8…+16 ms，所有 bridge time-domain 样本有效。
- PX4 日志的两个 duplicate IMU timestamp 错误单独保留，未证明与 cost lockout 有因果关系。
- 夹具移除，车辆 landed/disarmed；project.sh stop 后退出 0。没有 goal/compute-only/XY。

完整证据：[报告](../evidence/n08-health-lockout-readback-20261024-239.md)、[JSON](../evidence/n08-health-lockout-readback-20261024-239.json)；过程摘要：[dialogue](../../collaboration/dialogues/2026-10-24-239-n08-health-lockout-readback.md)。
