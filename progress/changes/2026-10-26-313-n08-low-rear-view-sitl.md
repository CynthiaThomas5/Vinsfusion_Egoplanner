# 2026-10-26 #313：低位后向观察 SITL 结果

- 目标：避开后向视角后的下降锁存，并清除 #310 的机尾侧 unknown 薄层。
- 静态输入：`n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view`，17阶段、462仿真秒；44项 profile tests、项目结构检查和 shell/JSON/diff 检查通过。
- SITL 结果：下降段先于最后 rear view 完成，未在下降时触发锁存；第14阶段同时 yaw−π/2→−π 和 pitch0→−0.35 时 normalized cost=1.022129 越过原1.0门限，13/17阶段后停止。无 post-release N05、N08 mission、goal、enable 或飞行。
- 安全：fixture detach/model removal/landed 已确认；独立 PX4/bridge readback 为 DISARMED、landed、DISABLED/control0，6秒控制 topic 零样本；仅停止 #313，容器 exited 0。
- 下一步：#314 保留低位 rear-view 和先下降顺序，只拆分 pitch/yaw 运动，定位哪种姿态变化造成健康代价增加。
- 证据：[运行报告](../evidence/n08-low-rear-view-lockout-20261026-313.md)、[JSON](../evidence/n08-low-rear-view-lockout-20261026-313.json)、[静态profile报告](../evidence/n08-low-rear-view-profile-20261026-313.md)、[SITL对话](../../collaboration/dialogues/2026-10-26-313-n08-low-rear-view-sitl.md)。
