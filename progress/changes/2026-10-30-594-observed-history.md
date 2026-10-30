# #594 显示专用累计观测地图

- 用户范围/模式：普通单项，添加RViz保留走过区域；不改规划地图，不自动扩展到保存加载/全局SLAM。对话：[摘要](../../collaboration/dialogues/2026-10-30-594-observed-history.md)。
- 新增：uav_mapping的体素历史缓存/ROS节点、observed_history.json配置、setup入口与sensor_msgs_py/std_msgs依赖；默认可视化launch按同一session和planner配置启动；RViz新增青色历史图层。
- 行为：raw occupied云并集去重、容量限制/告警、保留晚订阅快照；map/epoch/时钟重置清空并拒绝旧会话。仅发布visualization，不读取真值或发布控制。与局部膨胀层可独立勾选。
- 验证工具：新增4项缓存单测、真实ROS生命周期probe并接入project.sh test、只读live历史保留观察器。文档更新mapping README/running；CURRENT与里程碑登记本次post-delivery范围，不改N17历史出口。
- 命令结果：build ros18包PASS；project.sh test740单测+3套ROS PASS；16m GUI/SITL全部7项qualification PASS；起点588/588体素在终点历史层保留，终点局部层0/588，累计5850体素。见[证据](../evidence/observed-history-20261030-594.md)与对应JSON输入哈希。
- 未解：历史点可能含漂移重影；不根据free删除，不代表当前碰撞；25万体素上限，无跨启动保存。均已在文档披露。
- 停止：功能与有界回归完成。GUI已落地上锁后保持供用户查看，其他项目进程不动；无自动下一任务、提交或推送。
