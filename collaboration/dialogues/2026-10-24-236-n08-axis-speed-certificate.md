# N08.2z #236 任务摘要

- #231 证书记录 Y 轴导数 hull 上界 0.08157 m/s；profile max velocity 0.075 m/s，EGO 每轴 5% tolerance 加 1e-4 的现行上限约 0.07885 m/s。
- 现有证书只检查 0.15 m/s 三维向量范数，故逐轴超限没有进入 `speed_pass`。#236 只补此检查并测试；不改参数或安全门、不重测 #198/#200/#204，不做 SITL/XY。

- #236 已完成：新证书要求 EGO逐轴界0.07885m/s和既有向量界0.15m/s都通过；#231的0.08157m/s Y界会被拒绝。只改证书与描述并加4项单测，7项N08相关测试通过。无SITL/XY；N08未通过。
- 证据：[报告](../../progress/evidence/n08-axis-speed-certificate-20261024-236.md)、[JSON](../../progress/evidence/n08-axis-speed-certificate-20261024-236.json)。下一步待共享负载/仿真时钟稳定后重做 #235 scan 并加只读事件时间线。
