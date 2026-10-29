#270：任务拒绝默认规划速度配置

## 目的与结果

#270 使用新 epoch 重跑 N05 后释放准入。N05 15/15完成、post-release及mission current-area在线／离线检查通过，40.003s preflight通过。但启动命令未设置 `D435I_PLANNER_CONFIG`，manifest 锁定默认 `ego_planner.json`（0.5m/s，0.8m/s²），mission gate 按设计拒绝；没有进入N08 runner。

## 安全状态

无 `flight.json`、目标、Offboard enable 或起飞。直接状态为 bridge DISABLED、control disabled、disarmed、landed；PX4 arming_state=1、land detector landed=true。`project.sh stop` exit0，容器 exit0。

## 后续修正

#271 启动命令显式设置 `D435I_PLANNER_CONFIG=config/components/mapping/n08_low_speed_trial.json`，先检查 launch manifest 的 profile path/hash/max velocity/acceleration 与试验配置一致，再让 N05 和 mission gates 执行。#270 的 map identity 不跨冷启动复用。

证据：[拒绝报告](../evidence/n08-planner-profile-guard-refusal-20261025-270.md)、[结构化记录](../evidence/n08-planner-profile-guard-refusal-20261025-270.json)。对话摘要：[270](../../collaboration/dialogues/2026-10-25-270-n08-launch-profile-guard.md)。
