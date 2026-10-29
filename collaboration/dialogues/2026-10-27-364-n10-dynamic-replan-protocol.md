# 2026-10-27 N10 #364：PX4 在线障碍重规划诊断协议

## 目标

补 N10.3 尚缺的 PX4 控制下动态障碍重规划证据。#363 确认静态障碍已有离线净空数据；N06 动态注入只覆盖 planner-only，所以要在现有 PX4 世界中验证实际闭环。

## 冻结决定

- 唯一变量：目标发出且首条 EGO B 样条已出现后12仿真秒，向 `vio_initialization` 插入一个固定 pose `(0,0,1.4)m`、尺寸 `0.8×0.8×2.8m` 的静态可见箱体。
- 运行配置继承 #361：同一 spawn、16m 单目标、horizon5/max_vel0.8/max_acc0.25、official_ego、单 D435i 和 PX4 唯一桥控制。
- 观测 map 对障碍的原始证据、同 goal/epoch 的新 traj_id、PX4实际运动、真值净空、contact、最终 landed/disarmed/control-disabled/zero-control。
- VINS quality/source-age 门限保持删除；不增加 raw-free whole-curve gate。真值只用于离线量测。
- 1秒内没有替代轨迹时，经既有 caller-cancel 并由 bridge 落地，作为诊断失败保留；1秒不是最终验收门限。

## 状态

协议已冻结，未启动飞行。下一步 #365 实现 run-local injector/observer 并冻结哈希，然后按协议运行。机器/文字协议见 `progress/evidence/n10-live-obstacle-replan-protocol-20261027-364.json` 与 `.md`。
