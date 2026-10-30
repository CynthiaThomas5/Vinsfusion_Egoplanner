# #595 对齐官方indoor.gif地图显示

- 范围/模式：普通单项；用户确认按官方README第三张图做累计障碍显示并弱化地面。对话：[摘要](../../collaboration/dialogues/2026-10-30-595-official-map-style.md)。
- 修改：新增uav_mapping/history_display.py及5项单测；observed_history增加filtered/raw/status三个显示专用输出；配置增加地面支撑条件与0.20m显示带。原raw缓存保留，不改planner/control/ground collision。
- UI：白底、TopDownOrtho、历史障碍Z高度配色；局部膨胀层默认关闭但保留入口。mapping README和running.md说明显示带、低矮障碍、平地假设、原始诊断与未变的规划规则。
- 验证：build ros18包、project.sh test745单测+3ROS集成PASS；一次新GUI16m任务qualification全部7项PASS；累计5803、显示1452、隐藏地面带4351；起点598/598原始体素保留。真实窗口截图检查通过。见[证据](../evidence/history-display-20261030-595.md)及JSON输入哈希。
- 产物：progress/evidence/history-display-20261030-595.{md,json}；artifacts/runs/gui-20261030-125353-3586249（包括截图）与history-display-20261030-595-checks。
- 局限：显示层低矮障碍可能被隐藏；只验证平坦仿真房间，非语义地面分割/实机/全局SLAM；同会话内存缓存不变。
- 停止原因：本轮完成。按用户查看需求保留正常落地上锁GUI；无自动下一任务、提交/推送。
