# #348 N10.3：按用户授权移除额外速度保护

对应对话：[授权摘要](../../collaboration/dialogues/2026-10-26-348-remove-extra-speed-caps.md)。目标：删除本项目额外0.12m/s运行取消门，以及取消停车总速0.10/垂向0.01m/s拒绝门，速度保持只读记录。

## 实际改动

- `tools/run_vio_ego_flight.py`：删除速度事件生成和自动取消路径；改为速度观测字段；任务超时仍按原action取消流程处理。新增`tools/test_speed_observation.py`核验超过旧门限的两类速度都只读记录，NaN样本不伪装为有效速度。
- `dependencies/patches/ego/0052-remove-cancel-stop-speed-caps.patch`：在0051之后移除取消停车两个数值拒绝条件；同步唯一vendor源码、sources.json顺序/补丁哈希/结果哈希。EGO规划max_vel/max_acc、碰撞/身份/新鲜度和唯一控制出口继续生效。
- N10任务profile去除max_actual_vector_speed_m_s；N10 planner候选移除旧n08_vector_speed_cap_m_s元数据，活动0.25候选说明改为新授权状态。
- 更新GOAL授权注释、官方规则对照、N10计划、CURRENT及milestones；补存已执行#347的失败和安全读回，不修改其原始数据。

## 验证命令与结果

- `bash tools/project.sh build ros`：PASS，17包，46.5秒。
- `bash tools/project.sh test`：PASS，407单测及navigation-adapter/official-policy ROS集成。
- `python3 tools/fetch_dependencies.py --source ego_planner --target /tmp/d435i-n10-348-ego-replay`：PASS，所有补丁重放与锁定哈希通过，完整源码与vendor逐文件一致。
- 安装binary核验：旧cancel_stop_speed_outside_n08_calibration字符串已不存在，新cancel_stop_invalid_velocity存在。
- 结构与diff检查见本轮evidence；结构检查不算飞行通过。

产物：[证据报告](../evidence/n10-remove-extra-speed-caps-20261026-348.md)、[JSON](../evidence/n10-remove-extra-speed-caps-20261026-348.json)，大日志在`artifacts/runs/n10-20261026-348-remove-extra-speed-caps/`。

本轮按用户新指令完成实现与验证后收尾，无新飞行会话；N10父目标仍未完成。新速度范围的跟踪、停车距离和长程/长时证据仍待实测；保留原低速停止距离策略不代表任何速度均可在该距离内停车。下一步冻结新输入协议后恢复N10.3完整16m/长时校准，不再用旧速度保护作为中断条件。
