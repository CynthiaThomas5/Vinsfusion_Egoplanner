# N06 yaw microstep reacquisition

- Goal completion mode 继续 N06；用户范围、原验收条件、unknown fail-closed 和不启动 PX4／controller／flight 的边界均不变。
- r23 首次 `n_pts size: 0` 在 sim 11.452 s／估计 yaw约0.557°／truth约0.616°。首个1°步进后的静态 hold 后段 feature count恢复至约111–113。
- 第二步自sim17.747 s开始后，feature count降到个位数；mapping health gate在sim18.844 s／估计yaw1.961°关闭。第一条invalid LocalizationStatus在sim18.910 s，reason=`normalized_cost_exceeded`，truth yaw约1.546°。MapStatus之后一直`input_ready=false`／`map_reset_acknowledged`。
- Input recorder完成105.604秒；441个采样depth与camera pose只到sim18.745 s，raw header和health/map/localization状态则覆盖完整窗口。没有snapshot输出。runner exit code未被保留；已确认项目container和匹配进程停止。
- 下一假设只将最大不间断转角1°降至0.25°，保留角加速度、静态hold时长和场景，用8步2°pilot核对能否跨越之前的失效点。profile在`config/components/simulation/n06_yaw_microstep_025deg_pilot.json`。
- N06.2全机扫掠、terminal/emergency hold、replanning handoff与故障拒绝还缺实际布局证据；N06/S4保持`in_progress`，next_goal仍为N06。
