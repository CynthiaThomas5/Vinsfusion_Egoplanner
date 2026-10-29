# N08 runtime goal-profile fingerprint refusal（#297）

状态：安全前置拒绝，不是取消试验结果。

本次全新冷启动完成 N05 支架扫描 6/6，post-release 与 mission 前 online/offline N05 均 `all_entry_phases_known_and_clear`；同一 epoch/map，夹具已脱离／移除。扫描工具在 cleanup service 处报 stale DISARMED 状态，独立 5 秒 PX4/bridge 只读回读确认 bridge `DISABLED`、control disabled、PX4 `arming_state=DISARMED`、landed，且控制相关 topic 均为 0。40.01 秒只读 preflight 通过。

mission 在 goal/enable 前拒绝：`trial_source_fingerprint_mismatch:config/components/navigation/n08_forward_braking_trial_goal.json`。#276 build manifest 锁的是旧 goal 配置（`6e64be89…`）；本次 cold-start runtime manifest 和当前 goal 配置均为新 SHA（`38f2a449…`）。该 JSON 是运行时任务配置，并未参与 C++ 编译，所以旧 build SHA 比较错误；它仍必须严格匹配本轮 runtime manifest。

已修复校验：只把该 goal 配置列为 runtime-only 时，仍逐字节比较实际文件 SHA 与本次冷启动 launch manifest；编译源码、runner 和其他运行工具仍按原规则严格检查。新增回归验证 manifest 正确／错误两种情况。后续离线评估缺 `position_command_history` 与源时间错误均来自 runner 未启动留下的占位文件，不能当作飞行数据。

安全收尾：失败后另做 4 秒 live readback，确认桥仍 DISABLED、PX4 disarmed/landed、控制输出 0；`bash tools/project.sh stop n08-cancel-highspeed-prescan-20261026-297` 完成，容器 Exited(0)。详见[运行产物](../../artifacts/runs/n08-cancel-highspeed-prescan-20261026-297)与[机器可读记录](n08-runtime-profile-manifest-refusal-20261026-297.json)。
