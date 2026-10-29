# N07 #188：支架扫描后定位健康锁存，未进入飞行

**结果：FAIL_NO_FLIGHT；N07连续计数保持0/3。** 运行目录：`artifacts/runs/n07-20261024-188-01/`。

## 固定条件与扫描结果

新epoch `cf817e1c8021427db5c6b0b12ca05128`，map `cf817e1c8021427db5c6b0b12ca05128-035a28f5001a4d5c99a7a2d0a452bef3`。固定镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`、embedded runtime contract SHA `12b1c17cccfcb5c9f035516baa3d40c05ab7b8a4d5c32c4e28bef47d15b46233`、spawn `-6.5,0,0.3,0,0,0`、wall布局和 `n06_full_airframe_retreat_240_oblique_separated_return` profile；健康、N05与悬停门限未改。

初始 online/offline N05 同 epoch/map，均因 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` 拒绝；这是未扫描起点的预期拒绝。全机支架路线完成12/12，ready marker记录 attached、`vehicle_arming_state=1`、无truth输入、无control/goal发布。按流程等待2.000072464秒后，attached N05 online接受 `all_entry_phases_known_and_clear`；offline replay 与在线结果一致。snapshot/source/fusion age 为0.112/0.156/0.040秒，均在原0.4秒门限内。

## 释放后失效与判定

请求释放后，helper以原始错误 `fresh DISARMED status is required for every fixture command` 退出1。它记录12/12完成、attachment为attached→detached、fixture已移除且 `fixture_may_remain_attached=false`；remove-service未确认，但场景模型列表确认扫描fixture不存在。该helper结果仍保留为failed。

独立ROS读回：PX4 `arming_state=1`；`VehicleLandDetected` 为 `landed=true`、ground contact和at-rest；bridge `DISABLED`、`armed=false`、`control_enabled=false`、`landed=true`。但 `/localization/status` 已为 state 4、`valid=false`、reason `telemetry_stale`，bridge reason 为 `localization_not_tracking`。状态消息继续发布，传播源时间停在sim 455.920秒，accepted optimized/propagated计数停在6767/111678。因此没有运行post-release/current-area N05 gates，没有14/14 N05总结，也没有发送起飞、解锁或目标命令。

失效后12秒只读流探针记录到561个事件：相机图像最大源间隔≤0.036秒、IMU≤0.004秒、VINS telemetry和raw odometry最大源间隔≤0.068秒、最大收件间隔分别约0.0823和0.0822秒，最大clock-age为0.064秒；状态输出持续发布但仍为 `telemetry_stale`。这证明观察窗内输入流已恢复新鲜，**不能确定更早触发健康锁存的具体流或时间点**。此次定位失败按fail-closed保留，不据此修改健康门。

安全收尾：独立PX4/LandDetected与Gazebo读回确认DISARMED、landed、扫描fixture不存在。`bash tools/project.sh stop n07-20261024-188-01` 后容器 `exited 0`，无活动本轮容器。由于定位未跟踪，N07未进入飞行验收，连续通过数仍为0/3。原始产物逐文件SHA见[JSON证据](n07-preflight-postscan-localization-failure-20261024-188.json)。

## 下一步

#189保持同一镜像/runtime/spawn/layout/profile和全部健康/N05门限。唯一诊断变量是把只读VIO freshness probe提前到ready marker后并贯穿释放后决策窗口，以记录锁存发生时的流时间线；同时释放后先做必要状态确认，再尽快运行post-release/current-area gates。定位未恢复tracking或任一门拒绝时仍不飞。
