# N08.2q #227：live 曲线速度与 raw-map 几何证书

## 当前范围与假设

- 唯一主要变量：EGO `max_velocity_m_s` 从 0.15 降至 0.075 m/s；其他 EGO 参数、目标、N05/N06 门限不变。
- 假设：把 per-axis 速度配置降至 0.075 m/s 后，实际 B-spline 的导数控制点向量范数可被 0.15 m/s 显式上限覆盖。
- 判据：同一 compute-only run 的 B-spline 与 map identity 匹配；解析导数凸包上界不超过 0.15 m/s；same-run raw occupancy 中起始和终止 hold sphere、以及按生产 swept-curve 覆盖法计算的完整曲线均全 free。任一项失败即保留 no-go。
- PX4 只读增加水平参数实际 boot-time `px4-param show` 读回；最大限值不解释为最小制动能力。
- 仅 compute-only；bridge 输入保持隔离。没有 XY 指令、制动或执行授权。

## 预期产物

- 专用 EGO profile、live B-spline/map snapshot recorder、可复算 certificate、PX4 水平参数读回、轻量证据与命令记录。
- 验证包括脚本语法／静态解析、现有 structural check 和一次全新 N05-gated compute-only run；该 run 的曲线证书是本子项唯一判据。

## 完成条件

- 保存原始 run、manifest、PX4 boot readback、matching B-spline 和 raw occupancy snapshot；证据注明通过或失败及首个失败查询。
- 如果 speed、identity 或几何门未通过，不进入 N08 execute 或 XY；记录下一解除条件。

## 运行结果

- #01 未做支持扫描，fresh N05 current-area online/offline 因起降包络 raw unknown 一致拒绝，未启动 N08 runner。
- #02 支持扫描完成 15/15，post-release/current-area N05 online/offline 在同 epoch/map 通过；compute-only 在发送 goal 前因 `telemetry_stale` 锁存 fail-closed，未观察到目标或 B-spline。PX4 读回只有最大运动限制，不是最小制动能力。
- 两次均无 XY。#225 曲线回放确认速度上界计算器与 #226 一致，但不是 #227 新 profile 的曲线证据。N08 execute 继续锁定；具体记录见 [#227 证据](../evidence/n08-vector-cap-precondition-20261024-227.md)。
- 下一子项 #228 增加只读 ROS source/receipt timeline；本轮不因该答疑启动仿真。
