# #303 N08 负侧视后健康门拒绝

- 记录 #303 新冷启动结果：15/19 支架阶段完成，负 Y 侧视与回中完成；第 16 阶段 yaw0/z1 中立保持期间 cost=1.0007072056 触发原有 1.0 健康门。
- 初始 N05 原始地面候选不足，未执行 post-release gate；无 mission／goal／飞行。fixture 清理和 landed 状态通过验证，独立 PX4 读回 DISABLED、disarmed、landed、control0；容器 Exit(0)。
- 不改变阈值。#304 计划只缩短负侧到位后的 18 秒静止观察至 8 秒，其他运动和判据不变。

证据：[报告](../evidence/n08-negative-side-recovery-hold-refusal-20261026-303.md)、[JSON](../evidence/n08-negative-side-recovery-hold-refusal-20261026-303.json)、[原始运行](../../artifacts/runs/n08-cancel-highspeed-prescan-20261026-303/)。
