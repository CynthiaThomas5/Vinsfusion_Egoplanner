# P2 实际 ROS clock 回退故障注入

日期：2026-10-17。对话摘要：[2026-10-17-017-p2-clock-regression-replay.md](../../collaboration/dialogues/2026-10-17-017-p2-clock-regression-replay.md)。

- 修改：新增 `tools/clock_regression_relay.py` 与 `tools/probe_clock_regression.py`；run-local launch 将 Gazebo `/clock` source remap 到 relay，再向系统 `/clock` 单次发布1秒回退。触发条件要求 localization TRACKING 且 EGO occupancy 非空。没有改生产节点、vendor、项目参数、PX4 或控制。
- 结果：两次独立 live Gazebo D435i/VINS/localization/mapping/EGO run（domain193/194，不同 GZ partition 和 epoch）均通过。回退前地图峰值741／908点；定位 status 为 TRACKING 后转 `LOCKED/clock_regression`；mapping adapter 关闭门控并清理 map_id，plan_env 发送空地图。锁定时 EGO depth/pose 输出为10/10、15/15，optimized/propagated odometry 为19/248、9/111；settle 后至观察结束计数不变。运行图记录每条 depth/pose 各自唯一 RELIABLE publisher/subscriber，端点 QoS 兼容。详细数据和 artifacts SHA-256 见[证据](../evidence/p2-clock-rollback.json)。
- 排除 run：#01 launch runner 缺失且深度 remap 未 relay；#02 observer 晚于故障注入；#03 将 status state=4 LOCKED 误判；#04 EGO topic subscriber discovery 时序未捕获输出。四次日志均保留，不计成功。最终 #05/#06 的 source 与安装 overlay 哈希一致。
- 验证：两次 ROS 故障回放 probe exit0；继承的 mapping-input 4项、depth-gate 4项和 localization-health 9项单元测试通过（health 用例含 clock regression 锁存）；relay、observer 和 run harness Python／shell 语法检查通过；project structure check 仅表示结构／设计一致。没有改 package 源码，因此不重跑 colcon；构建与源码闭锁参照 P2 adapter/map-input 既有证据。
- 局限：此证据覆盖实际仿真时钟回退、定位 fail-closed、地图 reset 和输出停止；没有任务／轨迹状态节点，不能验证旧目标／轨迹取消。无 PX4、Offboard/Land、10分钟完整负载、几何或实机证据；GOAL E、P2 与 P4 均保持进行中。
- 清理：运行节点已退出；只停止本轮 domain188–194 的 ROS CLI daemon，未干预 domain186／187。未 stage、commit 或 push。
- 下一步：在完整 localization→mapping 链路对真实 VINS 进程重启做两次独立注入，验证旧 epoch map reset 与新 session epoch 隔离；继续任务状态机、PX4 bridge、地图几何／快照和完整控制故障策略。
