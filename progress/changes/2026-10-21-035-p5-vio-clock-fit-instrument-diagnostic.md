# 修改与验证记录

- 任务 ID／日期：#035 / 2026-10-21
- 对话摘要：[任务摘要](../../collaboration/dialogues/2026-10-21-035-p5-vio-clock-fit-instrument-diagnostic.md)
- 修改文件：新增 #391 run manifest、轻量证据和对话／改动摘要；更新 GOAL 进度复核、README、CURRENT、evidence index 和 P5 milestones evidence link。运行产物保存在 `artifacts/runs/p5-vio-px4-clock-fit-instrument-20261021-391/`。
- 行为变化及原因：canonical 源码和配置没有变化。run-local bridge 的两处速率越界异常只增加诊断数字，测试通过后编译为独立 overlay。#391 attempt-03 的 4.0 秒低频遥测门让 no-truth smoke flight 通过前置窗、到达近原点高度目标并安全降落；mapper越界没有重现，随后 VINS `normalized_cost_exceeded` 触发定位失效与降落。前两次 attempt 在 SITL 启动前因 run-local 模型路径失败，均保留日志。
- 验证类型：静态、容器构建和 SITL 诊断。
- 命令与结果：run-local synthetic mapper exception 检查 PASS；三个 run script `bash -n` PASS；attempt-03 `colcon build --packages-up-to uav_px4_bridge` 6包 PASS；`d435i-vins:dev` no-truth SITL harness PASS，`action_result=succeeded/position_yaw_tolerance_held`，最终 `landed_and_disarmed=true`。control topic publisher counts 均为1，ROS topic list和 bridge节点信息未见`debug_truth`。
- 证据及解释：[轻量报告](../evidence/p5-px4-vio-clock-fit-instrument-diagnostic-20261021-391.json)，[run manifest](../../artifacts/runs/p5-vio-px4-clock-fit-instrument-20261021-391/run-manifest.json)。PX4 ULog 中 EV aiding fused；EKF2 GPS control 参数为0，GNSS aiding flags全零，但 ULog仍有GPS传感器消息。该轮仅为隔离4秒门下的 smoke，不满足canonical 3秒门，也没有障碍绕行，不能作为 P5 或 GOAL D/E 验收。
- 未验证与 PROVISIONAL：#390 `clock_mapping_rate_out_of_bounds` 未在 #391 复现；instrumented mapper报告只有启动期`clock_mapping_not_converged`。4秒门仍是run-local诊断参数，VINS在动作后以normalized cost门退出。没有真值误差、机体净空、多场景冷启动、故障注入或10分钟负载证据。P5维持in_progress，A–H状态不变。
- 下一步：canonical 3.0秒门下做控制关闭、同负载配对采集，关联 bridge 对 estimator_flags／land_detected 的接收时刻和源时间戳、`/clock` monotonic回执及RTF；解决接收龄前置门后再重复零偏移飞行与场景验收。
