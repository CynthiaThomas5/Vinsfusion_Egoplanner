# 任务对话摘要

- 日期与任务 ID：2026-10-21 / #036
- 用户目标与明确约束：继续推进 GOAL.md 的 P0–P6 单 D435i 仿真导航；保留工作区已有修改；canonical遥测龄限值保持3秒；运行图不得订阅 `debug_truth`；PX4控制设定点和OffboardControlMode由 `uav_px4_bridge` 独占发布；阶段通过必须有对应证据。
- 已确认的决定：#392用CPU与canonical配置做无控制基线；RTF不足后不放宽门限，而在可用RTX 3060上复测。#393无控制探针通过后，#394运行canonical门控的零相对位移／零yaw目标；之后用#395长时静置和#396无导航目标受控悬停区分失效边界。回执埋点只写在run-local桥接副本，不更改canonical源码、参数或发布者。
- 运行结论：#392 RTF 0.2898，5秒PX4遥测稳定门失败。#393 GPU RTF 0.6238，canonical 3秒门通过5秒稳定检查。#394目标action报告成功，出现1218条同epoch READY命令，PX4 ULog观察到EV aiding，GNSS aiding flags为零，最终安全落地／解除武装；随后 `normalized_cost_exceeded` 触发定位锁定和桥接降落。#395在无控制后门观察中额外运行45秒，状态仍TRACKING。#396通过5秒稳定门，执行30秒无目标定点悬停并安全落地，0条PositionCommand、无导航目标，未复现定位锁定，VINS cost峰值0.6334。
- 解释边界：#394与#395/#396的差异支持将cost越线与EGO目标／轨迹活动关联，仍是小样本时间相关性，无法区分规划轨迹、任务完成／取消顺序或其他运行差异。#394是零相对位移／零yaw hold目标，没有障碍绕行或正式净空测量，不作为P5、GOAL D/E或最终验收。
- 待办：在同一GPU与canonical 3秒门下重复零相对位移目标，记录action、READY轨迹、VINS cost和landing时序；如复现再做单变量轨迹消融。保持真值隔离和桥接唯一控制出口。
- 对应改动记录：progress/changes/2026-10-21-036-p5-gpu-canonical-hover-diagnostic.md
