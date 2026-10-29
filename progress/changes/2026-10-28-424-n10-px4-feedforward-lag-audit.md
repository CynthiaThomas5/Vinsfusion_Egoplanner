#424 N10.3 PX4 跟踪延迟诊断

- 将离线 PX4 setpoint/state 滞后扫描扩展为同样本对照，防止不同 lag 的样本数变化制造虚假最优值；新增两项合成数据单测。
- 对 #381/#385/#412 分别复算。固定 40 ms 括区、同一本地状态样本下，1.06 s 回看使 RMS 从 0.534/0.511/0.275 m 降至 0.037/0.034/0.028 m；样本数分别 1645/1025/444。0–3 s 全网格共同覆盖为零，因此不报告整条 lag 曲线结论。
- 源码审计：EGO 输出当前轨迹位置；桥接器虽然计算 NED velocity/acceleration，却只发布 position，feed-forward 字段为 NaN。锁定 PX4 PositionControl 支持位置 setpoint 携带非 NaN 速度前馈。省略前馈是待因果测试的实现假设，不是已证明根因。
- 验证：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.test_n10_px4_tracking_lag`（2项通过）；`py_compile` 与 whitespace 检查通过；三个离线评估器归档回放退出码均为0。
- 限制：没有改运行源码／参数、没有构建或 SITL。#415 未安全收尾前，不实施桥接修复或 N10.5。
- 证据：[N10-424](../evidence/n10-px4-feedforward-lag-audit-20261028-424.md)。
