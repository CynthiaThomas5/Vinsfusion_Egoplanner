# P5 75秒PX4 estimated_offset周期复核

- 延续完整GOAL，不缩小 P0–P6/A–H范围。#112为75秒被动SITL，没有控制发布、真值输入、enable、解锁或飞行。
- 新domain228/partition/build副本中收到473条VIO并观察EV position/yaw融合，GNSS aiding全零；控制样本零且disarmed。
- 观察到estimated_offset重估两次：12.814–18.340s和44.706–49.988s。`px4_telemetry_stale` detail两簇共70/576，分别12.954–18.554s和44.853–49.954s。平台段源龄恢复为毫秒级。
- observed_offset墙钟斜率约−0.5824，/clock仿真率约0.4176，两者绝对值和约1；estimated_offset平台期间 observed_offset继续漂移。#112两次出现 `estimated_offset=0` 后立即按observed_offset重建估计，是Timesync filter reset的直接状态证据。PX4源码中高偏差与DDS会话删除均可reset；Agent日志没有重连，因此高偏差reset最可能，但内部计数器/debug事件未直接观测。
- readiness仍为DISABLED下preflight失败；P5不通过。证据：[progress/evidence/p5-px4-offset-cycle-75s-20261017-112.json](../../progress/evidence/p5-px4-offset-cycle-75s-20261017-112.json)。下一步量化Timesync、lockstep `/clock` 与Agent wall-clock的时基关系，再验证仿真专用处理。
