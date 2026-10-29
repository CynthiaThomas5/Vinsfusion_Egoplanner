# N08 #311：rear-facing 支架扫描拒绝

- 用户目标仍为 N08 单程前向目标；到点停止，无自动返航。
- #311 新 rear-facing support profile 在 stage 7/17 的 x 回程阶段以 normalized cost 1.048986 超过原 1.0 门限；发生在修改的 12 s 下降阶段之前。
- VINS cost components 显示 visual cost 2389.14/4808 residuals；IMU、bias 正常。#309 同路径在 x≈−0.46 m 越线，#310 通过，#311 在 x≈−0.985 m 越线，位置不固定、run realization 有差异。
- 新增下降时间变量未被触及。本轮不计 profile 通过、不计 N08 证据。fixture 移除，PX4 DISARMED/landed，bridge DISABLED/control0，容器 Exit(0)。
- 下一步仅延长同 profile stage 7 的 1.2 m 回程时间 60→100 s，检验较慢观测回程对视觉 residual 的影响。若再次在该阶段健康锁存，停止该路线的时长微调。
