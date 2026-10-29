# N06 slow-yaw diagnostic

- 用户通过 `codex resume --last` 恢复 Goal 完成模式，范围 N06。
- r21 只有一个主要变量变化：固定位置、同 surround、同 360° yaw 端点下峰值速率降四倍。mapping log 显示首个 `n_pts size: 0` 在 sim 17.194 s（VINS yaw 0.61°）；首次 map health gate closure 在 sim 45.574 s（`normalized_cost_exceeded`，VINS yaw 16.37°）。相较 r20 锁定较晚，但未走完全转。
- 15 秒 docker stop 到期导致 exit 137，VINS log 保留，motion truth 与 input capture 未落盘。已确认项目 container/Gazebo/VINS/EGO 等进程已停止。
- 下一假设：每 15° yaw 由静止加速再减速，随后静置 5 秒，让 feature tracker 在固定视角重获；保留 r21 的峰值角速度与环境。新 profile 是 r22 前置，尚未运行。
- 为中断时保存 partial records，runner host cleanup 宽限改为 90 秒；下一次 health lock 通过容器内 SIGINT motion process group，使 shell cleanup 有序结束 recorder 与 stack。
