# P5 低动态 EGO 参数源与 preflight 诊断（#188–#190）

## 改动

- 新增 [ego_planner_slow_probe.json](../../dependencies/retired-code-20261021.json)，保留默认规划配置，单独使用0.25 m/s最大速度和0.4 m/s²最大加速度作 PROVISIONAL 诊断。
- [vio_ego_bringup.py](../../src/own/uav_px4_bridge/uav_px4_bridge/vio_ego_bringup.py) 与闭环 launch 增加可选的项目相对 `planner_config` 参数；拒绝项目根目录以外的路径，并将选用文件纳入运行 manifest 哈希。
- 更新配置／bridge 文档，添加配置选择契约测试。
- #190 的 `pre_flight_checks_pass` 等待逻辑仅在 run-local harness 内，不修改 canonical bridge 或 PX4 行为。

## 验证

- `python3 tools/test_vio_ego_bringup_config.py`：6/6通过，包含参数注入、manifest哈希和路径边界。
- `python3 -m py_compile ...`：resolver、launch 与测试文件通过。
- 固定 Jazzy `colcon build --packages-select uav_px4_bridge`：1/1通过；安装前缀与 launch `planner_config` 参数 smoke 通过。
- `python3 tools/project_status.py`：结构／设计检查通过，不代表阶段验收。
- #188–#190 manifest 均记录低动态配置及匹配 SHA-256，但三轮都没有执行导航目标：#188 freshness 锁定，#189 PX4 preflight 未通过，#190 preflight 守卫拒绝 enable。每轮独立只读真值采集完整且无解析错误。

## 限制与下一步

没有低动态轨迹结果，不能判断速度／加速度变化是否改善 VINS 视觉代价。PX4 `pre_flight_checks_pass` 间歇为false和优化里程计0.304秒 freshness 超限仍需诊断；不下调门限。P5与P6保持进行中／未开始。

详见 [运行证据 #188–#190](../evidence/p5-vio-low-dynamics-preflight-20261019-188-190.json)。
