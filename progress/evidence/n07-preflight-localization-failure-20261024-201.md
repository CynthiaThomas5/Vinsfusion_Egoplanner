# N07 #201：IMU 时间戳超前导致起飞前拒绝

## 结果

**FAIL_PRECONDITION；连续通过数从 1/3 归零为 0/3。** 独立冷启动目录：[n07-20261024-201-01](../../artifacts/runs/n07-20261024-201-01/)。N07 保持 `in_progress`。

no-goal runner 在起飞前因 `vio_bridge_map_preconditions_not_ready` 退出；bridge 为 `DISABLED`，定位状态 `state=4, valid=false, reason=imu_from_future`。没有发送目标或起飞命令，没有进入 ACTIVE/armed，也没有悬停。

## 固定条件与 N05 结果

运行使用固定镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`、runtime 配置 SHA-256 `1ddd6838ae2a678f89547ce90eea849582edcc29cddab341667bd2d1d9d3e360`、runtime-contract 文件 SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、spawn `-6.5,0,0.3,0,0,0`、`wall_box_column` 与 `n06_full_airframe_retreat_240_oblique_separated_return`。原门限未改，也未启动可选 freshness probe。

- 初始 online/offline N05 gate 一致 fail-closed：`ground_plane_insufficient_raw_occupied_voxels`。全机支架路线 12/12 阶段完成，attachment `attached → detached`，fixture helper 报 `outcome=failed`、错误 `localization changed or became invalid during physical scan`；remove RPC ack 与 Gazebo scene absence 均为 true，最终 landed 经独立读回确认。这个 helper 错误原样保留。
- N05 summary 14/14 通过；扫描后、post-release、current-area online/offline gate 均接受 `all_entry_phases_known_and_clear`。current-area freshness：snapshot 0.120s、depth source 0.112s、fusion 0.068s，均在原 0.4s 限值内；identity 与 post-release 一致。
- fixture trace 13,361 行、单 epoch、0 条无效定位记录；独立 PX4 启动参数审计通过。起飞前释放安全读回 11/11 通过。地面平面只用于起降／接地准入；本次没有地下目标或地下飞行。

## 定位时序证据

适配器日志的 `health_future_observation` 记录：仿真 `/clock` 为 **550.440s** 时，IMU 源时间为 **550.488s**，领先 **48ms**；冻结的 future tolerance 为 **20ms**。`LocalizationStatus` 随后锁存为 `imu_from_future`，bridge 拒绝定位前置。确切的时间戳超前来源尚未确定，现有证据不能区分仿真时间戳与消息发布时间／传输顺序。

同一窗口内 `/clock` 无倒退；VINS raw odometry 到 618.356s、求解 telemetry 继续且 solver usable（末尾 normalized cost 约 0.453），depth health 仍有效、占据云没有大间隔。对齐记录窗口未收到 `/localization/optimized_imu_odom` 输出，状态源时间停留在 550.436s。证据表明时间健康门触发后定位适配输出停止；这不是 VINS solver 质量门失败。

Graph waiter 因 flight 结果先于 ACTIVE+armed 写出而未捕获活动图；唯一控制 publisher/no-truth、hover evaluator 与 airborne ULog 条件均未通过或未执行，不能用 N05 或 PX4 boot audit 代替。

## 安全收尾与下一步

最终独立安全读回 11/11 通过：bridge disabled/control off、PX4 DISARMED/landed、fixture 不在场景中、没有活动 flight/observer。`bash tools/project.sh stop n07-20261024-201-01` exit 0；容器 `exited 0`，活动项目容器数为 0。运行证据没有修改项目源码、配置或验收阈值。

#201 使当前连续通过数归零。下一项 #202 从新的独立 cold start 开始，保持固定 image/runtime/spawn/layout/support profile、observer set 和原门限；不放宽 `imu_from_future` 安全门。根因仍待进一步证据确认。

逐文件 SHA-256 与机器可读判定见 [JSON 报告](n07-preflight-localization-failure-20261024-201.json)。
