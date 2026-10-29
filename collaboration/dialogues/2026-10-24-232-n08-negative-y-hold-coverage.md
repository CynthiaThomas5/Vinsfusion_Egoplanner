# N08.2v #232 任务摘要

- #231 的 same-run start hold query 有 209 个 unknown，cell centers 集中在起点相对 ENU `Y=-0.93…-0.83 m`。
- #232 保持目标、scene、释放位姿、planner 和门限不变，仅切换 N05 support profile 到已有 `n08_overhead_rear_one_side_view`（yaw −π/2 侧向视角）。
- 假设：新鲜负 Y 观测能补齐 start-hold unknown。判据：fresh N05 gate、compute-only READY、same-identity map 上 body/hold/curve/0.50 m stop corridor queries。
- 仅 DISARMED scan 与 bridge-isolated compute-only；停止包络未证明前不执行 XY。
- #231 的 0.15 m/s vector certificate 未验证配置 per-axis 0.075 m/s；捕获曲线 Y derivative hull 为 0.08157 m/s。#232 记录此实现/验收缺口，不降低标准。

## 实际结果与交接

- #232 在 stage 9/19 中止，helper 读到 `normalized_cost_exceeded` 1.702；最后 trace 样本仍 valid，因此异常转换时刻没有证据。
- 该 profile 先执行 yaw +π/2、pitch −0.45，随后才会执行 yaw −π/2 水平观察；失败发生在前一观察段，负 Y 视角未达到。post-release gate 与 compute-only 均未运行。
- 车辆 landed，fixture detach/remove 已确认，仿真容器停止 exit 0；无 XY。
- 下一项 #233：保留 overhead scan，只替换成隔离的 −π/2、pitch 0 观察并回中；N05 gate 通过后才运行 compute-only。
- 证据：[报告](../../progress/evidence/n08-negative-y-hold-coverage-20261024-232.md) 和同名 JSON。
