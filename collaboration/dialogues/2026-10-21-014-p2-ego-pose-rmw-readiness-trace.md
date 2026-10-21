# P2 / GOAL C EGO Fast DDS reader readiness trace #347

- **任务摘要**：在 #346 的配对观测后，直接测 EGO camera-pose RMW wait readiness 与 Fast DDS reader match/lost/rejected 状态，并与发布、take、callback、executor 事件、独立 pose reader 及 MapStatus 同窗对齐。
- **用户约束**：单 D435i 仿真；不订阅真值，不连控制器/PX4；保持 EGO QoS、0.4 s freshness 门和 unknown fail-closed。保留工作区已有修改；不暂存、不推送。
- **决定**：复用 #345 EGO binary 与 #231 预建 probe library；直接启动同一 mapping adapter console executable 取得明确 PID。失败的第一轮只做 preflight，保存后重跑到第二轮成功。分析器与状态采样都写明缺失序号和取样粒度，不能外推根因。
- **已确认**：EGO pose take 最大间隔2.482 s时，publisher与独立 reader都继续有数据；EGO reader wait大部分not-ready且无成功take，executor仍活动。Fast DDS sampled matched=1、rejected=0；sample_lost总计在gap后首个样本变为1，但128次wait采样间隔不能定位时点。全trace缺四个序号75–78，均在选定gap之外。Planner-only附带样条含42/103个起点unknown voxel样点，未执行；最近odom与spline start相差25 ms。
- **待决问题**：Fast DDS样本是否未进入reader history，或已进history但没有触发wait readiness；需要更细粒度unread/lost记录。GOAL C、GOAL D/F与A–H保持pending。
- **记录**：[改动说明](../../progress/changes/2026-10-21-014-p2-ego-pose-rmw-readiness-trace.md)、[轻量证据](../../progress/evidence/p2-ego-pose-rmw-readiness-trace-20261021-347.json)、[运行清单](../../artifacts/runs/p2-ego-pose-rmw-readiness-trace-20261021-347/run-manifest.json)。
