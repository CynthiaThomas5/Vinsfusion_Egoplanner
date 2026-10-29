#270：N05 通过，但 mission 因启动 profile 错误在起飞前拒绝

## N05 与 preflight

新 epoch `5670fae0742a49c68762342ebaec1fca` 的 N05 支架扫描完成 15/15；释放后在线／离线检查、mission current-area 在线／离线检查都接受并保持同一 map identity。扫描器保留 `localization changed or became invalid during physical scan` 的泛化警告，但最后定位有效、支架已确认脱离／移除。40.00334 s preflight 通过，optimized-odometry 最大回执间隔 0.12254 s，超 guard 计数 0。

## 拒绝原因

新仿真启动时没有显式提供 `D435I_PLANNER_CONFIG`，launch manifest 因而记录默认 `config/components/mapping/ego_planner.json`，其参数为 `max_vel=0.5 m/s`、`max_acc=0.8 m/s²`。N08 trial runner 只允许匹配的低速 profile `config/components/mapping/n08_low_speed_trial.json`（0.1 m/s、0.25 m/s²），mission 的 profile gate 因 `invalid_n08_planner_profile` 拒绝。

此拒绝发生在 N08 runner 启动前：没有 `flight.json`、offboard enable、解锁、起飞或 EGO 目标；#269 垂向沉稳条件没有测试。#270 的 N05 地图与准入不能移用到另一个 cold start。

## 安全末态

直接读回 bridge `DISABLED`、`control_enabled=false`、`armed=false`、`landed=true`；PX4 `arming_state=1`，LandDetector `landed=true`。`bash tools/project.sh stop n08-20261025-270-vertical-settle-retry` 退出码 0，容器 `exited`、运行状态 false、容器退出码 0。

## 下一步

#271 新 cold start 重做 N05，并在启动命令显式设置 `D435I_PLANNER_CONFIG=config/components/mapping/n08_low_speed_trial.json`；先核对 launch manifest 中 profile 路径、哈希、max velocity 和 acceleration，再跑 N05／preflight／mission。profile gate 未接受前不进入 N08 runner。
