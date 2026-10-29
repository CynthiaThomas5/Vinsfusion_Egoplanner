# N08 #295：识别有live证书的同时间轨迹交接

## 根因

#294 motion-cancel native flight、3秒PX4实测停止保持和最终landing均通过。原 evaluator 将同一source stamp `354.520 s`的旧 trajectory 1 与新 trajectory 2 状态相比较并拒绝。当前EGO在B-spline handoff事件中允许两条状态共享ROS clock时刻；旧、新位置差 `0.4919 mm`，两者并非同轨迹重复。

## 修复

独立评估器仅在 incoming trajectory 的 live spline certificate 精确以相同 source stamp 开始，且 goal/epoch 一致时允许这一种handoff。评估时间序列保留新轨迹状态；报告保留位置、速度、加速度、yaw差及轨迹ID。其它时间冲突、相同trajectory状态变化、无证书handoff、源时间倒退仍拒绝。motion-cancel额外要求报告中观察到旧ID→认证stop ID的交接。

## 验证与适用范围

- 新增单元测试覆盖证书匹配handoff、错误/缺失证书拒绝和同轨迹yaw冲突拒绝。
- `bash tools/project.sh test`：359项通过，navigation-adapter integration通过。
- 只读重放 #294 原始 flight、truth、odometry 输入：35项验收检查全部通过；完整指标及哈希见[#294回放报告](n08-cancel-stop-qualified-replay-20261026-294.md)。原先写出的FAIL报告保留，没有覆盖。
- 这是offline evaluator修复，未改变运动runner或PX4控制；后续冷启动runtime manifest会记录新evaluator SHA。N08其它出口仍未完成。
