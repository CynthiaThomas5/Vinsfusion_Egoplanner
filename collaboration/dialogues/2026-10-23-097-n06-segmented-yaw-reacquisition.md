# N06 segmented yaw reacquisition

- 用户通过 `codex resume --last` 恢复 Goal 完成模式，范围 N06。
- r22 在同一 textured surround 静止转向。首次 n_pts zero 在 sim 11.914s／估计 yaw0.92°，健康门在 sim12.970s／估计 yaw2.41°关闭，truth yaw约2.63°。首次15° hold直到sim20.117s才开始，因此粗分段未保护最早失效门槛。
- 后续 hold 的 VINS feature count 偶尔回升，但8,559条状态在首个 `normalized_cost_exceeded` 后一直无效，MapStatus未恢复。profile虽命令360°，debug truth累计337.75°。input recorder完成428s窗口，但有效forwarded depth/pose只有263帧，最后stamp在健康锁前；无snapshot或EGO probe。
- r22正常snapshot readiness超时退出，已确认无项目容器/进程。所有PX4及控制链关闭。
- 预备新假设：把最大不间断角度从15°降到1°，保持r22角加速度并每步静置约5.16s，先执行8° pilot。background motion/input recorder现增加显式signal handlers，以容器内SIGINT触发partial-save；host stop grace为90s。
- 当前N06/S4保持in_progress，next_goal=N06；N06.2两布局整曲线/hold/replan出口仍未通过。
