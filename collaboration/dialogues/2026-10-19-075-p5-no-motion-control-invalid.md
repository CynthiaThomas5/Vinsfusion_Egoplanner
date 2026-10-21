# 对话摘要：P5 #193 no-motion 对照失效

- 用户目标：继续完成项目 `GOAL.md` 的 P0–P6 单 D435i 仿真导航工作。
- 约束：PX4 控制由 bridge 独占；真值仅限只读评估；不放宽健康门或改写失败为通过；P5 的静态、回放、SITL 证据须分别记录。
- 决定：使用零位移、零 yaw goal 检查“只派发/保持目标”时的质量门行为；复用 #191/#192 的镜像、PX4/VINS 可执行文件与配置。
- 确认：PX4 bridge 在 quality crossing 前因 `px4_telemetry_stale` 进入 LANDING；后续 detail 显示 attitude/local-position 时间戳分别提前104/84 ms，超过65 ms future tolerance。`normalized_cost=1.12086` 出现在 AutoLand 和约0.766 m/s下降期间。
- 结论：该运行不是有效的 no-motion 对照，不能归因于目标派发或静态视觉。动作最终因 quality gate 中止并落地；threshold 和参数未改。
- 限制：首次 latch 的 failed-source detail 未采到，PX4 ULog 与 ROS `/clock` 未做额外时间映射。具体视觉/边缘化代价来源仍未确认。
- 下一步：离线检查 PX4 source-age/future-time 映射，再决定是否重做 no-motion 对照；不放宽65 ms门限。
