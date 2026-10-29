#270 对话摘要

- 使用新epoch，N05支架扫描15/15、释放后和mission current-area在线／离线准入、40.003s preflight通过。
- 启动未传`D435I_PLANNER_CONFIG`，manifest错误使用通用`ego_planner.json`，速度0.5m/s、加速度0.8m/s²；N08 mission profile gate拒绝，未进入flight runner。
- 直接读回bridge DISABLED/control disabled/disarmed/landed、PX4 arming_state1/landed；停止容器退出0。
- 下轮#271将显式选`n08_low_speed_trial.json`并先核manifest，不复用本轮地图；返航仍须原地转头约180°确认后向机头前方EGO飞行，不能倒飞。
