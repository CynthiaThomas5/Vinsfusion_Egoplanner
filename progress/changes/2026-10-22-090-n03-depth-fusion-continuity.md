# #090 N03 深度实际融合连续性

对话摘要：[N03 执行约束](../../collaboration/dialogues/2026-10-22-090-n03-depth-fusion-continuity.md)。

## 本轮范围

Goal 完成模式，用户指定 N03。N03.1 增加只读的阶段时序与有限队列诊断；N03.2 收集三次同版完整 idle SITL fresh epoch；N03.3 当前版验证深度断流与身份 reset。PX4 必须 DISARMED，不发目标或轨迹。

## 改动

- `MapStatus.msg` 与 mapping adapter 增加 depth 回调数、待处理队列当前值／高水位、drop 数及转发 monotonic 时间。
- EGO 第 0040 补丁在 plan_env 记录同步输入回调、实际 raycast／occupancy 完成、reset 后身份和计数，只发布只读 trace。
- 新增 `tools/probe_depth_fusion_continuity.py` 和纯指标测试；探针记录源戳、四阶段时序、map query、输入健康、map reset、arming state 与 cgroup 资源；故障模式只对深度做有界丢弃转发。
- 新增 `n03_depth_fault_bridge.yaml`，只将 Gazebo depth 输出改接 fault relay 输入。
- 更新依赖清单和 EGO patch README，锁定 0040 顺序、SHA256 与受影响 vendor 文件哈希。

## 已完成验证

- `bash tools/project.sh build ros`：通过，17 个 ROS 包构建完成。
- `bash tools/project.sh test`：通过，223 项回归通过。
- `python3 tools/project_status.py`：结构／设计检查通过；该检查不替代构建与 SITL。
- `patch --dry-run -R -p1 -d src/vendor/ego_planner < dependencies/patches/ego/0040-depth-fusion-continuity-trace.patch`：通过。
- 三个独立 150 秒 idle SITL 通过：`090-01`／`090-02`／`090-04`；分别 1740／1751／1764 次 plan_env 融合，最大融合间隔 0.104／0.108／0.112 sim 秒，最大源龄 0.156／0.156／0.152 sim 秒，队列高水位 4／3／4。三者 runtime contract SHA256 相同；PX4 全程 DISARMED，导航命令 0。
- 三次合格 epoch 中 `input_ready` 后的 steady 10 秒窗口，adapter dropped-depth 计数都保持在启动值 41，增量为 0；机器摘要记录各自的基线、窗口和计数范围。
- 保留失败 `090-03`：约 0.437 wall 秒触发既有 `telemetry_stale` 锁存，adapter reset map，未形成 EGO 融合，不计入三次通过。VINS/telemetry 后续仍输出；不改健康门限，后续按 N10 处理。
- 当前版深度故障运行 `090-fault`：300 帧转发后丢弃 2.015 秒；DepthHealth `READY→STALE→READY`，STALE 1.008 wall 秒；map_id 改变、reset ack 成功；旧身份查询 `map_id_mismatch` 拒绝，新身份下恢复 1571 次融合和 300 次 accepted query（最大源龄 0.184 sim 秒）。故障全窗融合门按预期关闭；不计作正常连续性样本。
- 正常运行球查询仍有 191–238 次 `no_fresh_fused_depth` 拒绝／次（约 32–40%），这些发生在新输入待处理而非已融合源变旧时。曲线准入路径读取最新完成融合且保留 0.4 秒门；服务拒绝单独报告，未修改服务／规划／健康行为。
- 完整证据：[报告](../evidence/n03-depth-fusion-continuity-20261022-090.md)、[机器摘要](../evidence/n03-depth-fusion-continuity-20261022-090.json)；原始运行目录为 `artifacts/runs/n03-fusion-20261022-090-{01,02,03,04,fault}/`。

## 当前状态与局限

N03 已按限定出口通过，milestone next_goal 已移至 N04。局限：`090-03` 的 telemetry stale 启动失败仍需 N10 处理；静态 idle 结果不替代 N09／正式任务的飞行期连续性，也不证明 raw 地图几何或动作安全。
