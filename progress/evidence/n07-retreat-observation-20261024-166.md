# N07 #166 冷启动失败记录

- **结论：** 未取得 N07 悬停资格，连续合格序列按出口重置为 **0/3**。
- **运行：** `n07-20261024-166-01`，fresh cold start；wall 布局，profile `n06_full_airframe_retreat_240_oblique_early_view`。
- **入口检查：** 初始只读 N05 online/offline 一致拒绝 `ground_plane_insufficient_raw_occupied_voxels`。没有绕过拒绝条件。
- **支架扫描：** 12 阶段中完成 7 阶段，在 sim 292.348 s、x≈−1.308 m 首次越过原有 accel-bias 限值：0.150655 m/s² > 0.15；记录中的最大值为 0.168070 m/s²。未生成 `n05-prescan-ready`，没有 attached/released 检查，也没有起飞或悬停。
- **安全收尾：** fixture 已脱离并从场景移除，LandDetected 全部为 true、PX4 全部 DISARMED，bridge 回读 DISABLED，控制未启用，项目容器退出码 0。
- **连续计数：** GOAL 的 N07 出口要求“同一固定版本连续 3 次”且“失败修复后重新计算连续次数”。因此 #166 失败打断 #165 开始的序列；#165 正向结果保留为独立证据，但当前连续计数为 0/3。#167 起重新累计，未更改门限或控制行为。

主要证据：

- [结构化失败报告](n07-retreat-observation-20261024-166.json)
- 原始运行数据：`artifacts/runs/n07-20261024-166-01/`
- 初始 N05 online/offline 报告 SHA-256：`1c24d050f2e2e408716f4974615d09c3af17882d1ceb79b2af332c5cd0604fe6`、`892a1a1ee48eb5a8dbdc1cdf5427bf5b864963f0573ca4555738deed65af5964`
- fixture result / trace / VINS / odometry SHA-256：`217ab2ff769b289c4d9118690891c1f8e164dc4882570838b0afa304bc9609ee` / `68208b42258895ab2393035018fca6df1f47b44773020baff748c535aeb52404` / `09b97821975dd8c65b6360af4e21870638bb014fdc69b71e1666b00705b57abb` / `3ef2946a8db9b62165dda9844035dbc2468ad4a8cbf0db67c2edcf011eadc096`

本次没有代码或参数更改；失败诊断不构成 N05/N07 通过证据。
