# P2 活动轨迹 stale 与 EGO 安全状态

- 关联对话：[任务摘要](../../collaboration/dialogues/2026-10-17-003-p2-ego-active-depth-stale.md)。
- 文件与行为：新增 EGO 补丁 `0008-queue-manual-targets-on-fsm.patch`，让手动目标回调只更新待处理目标，由 FSM timer 在安全状态消费，避免 callback 内对已加入 executor 的 node 调用 `spin_some`；EMERGENCY_STOP 中丢弃待处理目标。新增对应定向构建报告和活动 stale 运行证据，更新 EGO 来源清单、补丁说明、CURRENT、milestones、GOAL checklist 与接口契约。
- 构建：Jazzy 定向构建 `ego_planner` 1/1 通过，编译依赖包来自既有安装目录；完整 16 包构建证据仍独立引用，不因本次定向构建替代。
- 动态验证：run #07 在新 epoch `6d3c39bcd23145159d963ec19fc44bd7` 下，目标源时间 11.320–19.636 s 覆盖深度丢帧源时间 13.288–18.288 s。relay 接收595帧、丢弃78帧、恢复前转发341帧；depth health 转 `STALE` 后恢复 `READY`。EGO 对非零目标成功规划并进入 `EXEC_TRAJ`；同一运行中出现 `Depth Lost! EMERGENCY_STOP`、plan_env reset、点云清零及同 epoch 重建。不过 `EMERGENCY_STOP` 日志早于 mapping adapter 报告 `depth_stale` 约4.16墙钟秒，且 EGO 已打印 `now=10.495`、`last_occ_update_time=9.472` 的 timeout；因此该状态不能归因于 scheduled fault，不计活动 stale 响应通过。脚本退出码0，运行结束前成功查询 EGO node info，事后进程审计无活动测试进程。详见[运行证据](../evidence/p2-ego-active-depth-stale.json)。
- 诊断与排除：未修补的重复手动目标 run #05 在 stale reset 前因 nested-executor 异常退出，不计安全证据；单次目标 run #06 只作 map reset 辅助观察。两者保留在活动 stale 报告中。
- 局限与下一步：run #07 只确认目标回调修复和 map reset/refill，未确认注入 stale 导致 EGO 急停。EMERGENCY_STOP 只代表 EGO planner/FSM 状态；本轮没有 traj_server、controller、PX4 或控制发布者，不能证明飞行器实际停住。深度恢复后 EGO 仍保持 EMERGENCY_STOP；安全恢复规则、重复冷启动和实际闭环尚未验证。下一步重复活动 stale 并定义受控恢复路径，然后实现导航任务接口与唯一 PX4 控制桥。
