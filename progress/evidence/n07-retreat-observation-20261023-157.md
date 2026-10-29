# #157 N07 1.5m 后退观察

## 结果

- 新冷启动 `n07-20261023-157-01`，spawn `-6.5m`。1.5m 单轴后退/返回 profile 完成6/6阶段，10,073/10,073 trace 均为 VINS valid、同一 epoch；normalized cost 范围 0.074–0.625，加速度 bias 峰值 0.045638 m/s²（门限0.15）。PX4 DISARMED、bridge DISABLED，支架 detach 与场景移除均有确认。
- 初始 N05 live/offline 一致拒绝。扫描后 attached N05 和 released fresh N05 仍一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。released HOLD unknown=6；TAKEOFF_CONTACT 最大 unknown=222、ASCENT/DESCENT=225、LANDING_CONTACT=222。offline replay 与 online gate 一致。
- 逐格审计：6个 HOLD unknown 中心均在 x=−0.55…−0.05m、y=0.35m、z=1.15m；raw ground plane z=−0.25m，地面以下 unknown=0。它们形成一条薄的地面以上未知带。
- 没有起飞；N07合格悬停仍0/3。

静态路线证书最小连续净空下界1.189m：[route geometry](n07-retreat-150-route-geometry-20261023-157.md)。完整运行哈希及原始数据见机器报告[n07-retreat-observation-20261023-157.json](n07-retreat-observation-20261023-157.json)和[`artifacts/runs/n07-20261023-157-01/`](../../artifacts/runs/n07-20261023-157-01/)。

## 下一项

1.5m 已提供充分定位余量但仍留6个 HOLD unknown。#158 将唯一主要变量改为后退距离1.8m，继续保持姿态、阶段时长、spawn和 N05 门槛不变，以移动这条窄未知带进入更远的有效深度视场。只有 released gate 通过才开始第一次无目标悬停。
