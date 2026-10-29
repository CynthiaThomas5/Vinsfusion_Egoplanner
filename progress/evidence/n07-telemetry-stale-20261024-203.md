# N07 #203：PX4 遥测时间戳领先触发安全中止

## 结果

**FAIL_SAFETY_ABORT；连续合格次数仍为 0/3。** 独立冷启动目录为 [`n07-20261024-203-01`](../../artifacts/runs/n07-20261024-203-01/)。N07 保持 `in_progress`，下一次为 #204。

N05 支架路线完成 12/12 阶段、summary 检查 14/14；post-release 与 current-area online/offline gates 通过。支架 helper 的错误 `localization changed or became invalid during physical scan` 保留在原始结果中，支架最终 detached/removed 并确认落地。飞行前置通过，runner 短暂进入 TAKEOFF/ACTIVE，随后触发 `telemetry_stale` 并安全降落。没有发送导航 goal；悬停只有 0.164 仿真秒，未达到 30 秒验收时间，不能计为通过。

## 时间戳失效证据

`flight.json` 的首次 `px4_telemetry_stale` 事件将 `attitude`、`land_detected`、`local_position`、`vehicle_status` 列为不新鲜来源。它们相对 `/clock` 分别领先约 196、180、196、128 ms；固定未来容许上限为 65 ms。`px4_time_domain_valid` 当时为 true，但这些来源的未来时间差仍超限。记录中 `timesync_sample_count=0` 且 `uxrce_dds_time_sync_enabled=false`；为什么 PX4 来源时戳领先仍未确定。

N05 初始地面接触／起飞 gate 的结果记录在机器报告中。它只决定已落地状态下是否允许起飞，与本次进入 ACTIVE 后的 PX4 遥测时间戳失效无关。地下空间仍不作为飞行区域。

## 图审计与收尾

只读 ROS graph audit 的控制发布者归属和无真值检查通过；但 ACTIVE 窗口太短，没有取得合格的 airborne graph snapshot。因为没有 30 秒悬停，独立悬停 evaluator 未运行。原始 PX4 ULog（130.8 MB）已保留；固定镜像缺少 `pyulog`；随后使用隔离的 pyulog 1.2.4 分析环境完成 ULog 核验，EV position/yaw、GNSS flags never-active 与最终 landed/disarmed 检查通过。该结果不补足 30 秒 hover 要求。

独立 postflight 读回 13/13 项通过：bridge `LANDED`、控制关闭、未武装；PX4 `arming_state=1`；land detector 有 ground contact 且 landed；支架模型不在 Gazebo 场景；无 flight/observer 进程。`project.sh stop` 返回 0，容器退出码 0，活动项目容器数为 0。

## 固定条件与下一步

本次保持 pinned image、runtime、spawn、layout、support profile、observer set、hover 命令和所有门限不变；没有修改源码、配置或验收阈值。N05 地面 gate、飞行前置和安全降落都按原标准执行。

下一项 **N07.50 #204**：新的独立 cold start，复用同一冻结条件与原门限。继续保留 PX4 时间戳健康保护；N07 需连续 3 次各完成不少于 30 仿真秒无目标悬停，并提供 EV/no-GNSS、独立评估、图审计和落地上锁证据。

逐文件 SHA-256 与机器可读结果见[JSON 报告](n07-telemetry-stale-20261024-203.json)。
