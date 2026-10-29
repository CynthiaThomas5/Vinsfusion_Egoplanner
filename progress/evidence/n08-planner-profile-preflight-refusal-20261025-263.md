#263：支架释放后 N05 通过，N08 速度 profile 指纹门拒绝

## 结果

新的同 run N05 全机支架扫描完成 15/15 段。支架解除、Gazebo 确认 fixture 不存在，867 个 PX4 status 样本均为 DISARMED、455 个 landed 样本均为 true。扫描前 N05 拒绝；扫描后和释放后在线／离线 N05 均以 `all_entry_phases_known_and_clear` 接受，epoch、map_id 连续，pose 转移在预算内。mission 入口另一次 fresh N05 也接受，40.00 秒只读导航 preflight 通过，最大优化里程计回执间隔 85.0 ms。

支架工具仍把 `fixture-result.json` 标记为 `failed: localization changed or became invalid during physical scan`，虽然 15 段均完成，轨迹中记录的 15,895 个定位样本全为 `TRACKING/valid` 且同一 epoch，最大 normalized cost 0.652；最终定位有效。这个通用收尾错误保留为未完全归因的限制，不能把 `diagnostic_pass=true` 当作飞行通过。当前运行的 post-release 与 mission 当前区 N05 新鲜准入，为后续继续提供了独立 gate 记录。

随后 mission 在发送任何航点前，以 `invalid_n08_planner_profile` 退出。原因已明确：本轮忘记将 `D435I_PLANNER_CONFIG` 传给新的 SITL，launch manifest 因而记录默认 `config/components/mapping/ego_planner.json`（逐轴 `max_vel=0.5 m/s`、`max_acc=0.8 m/s²`）。N08 执行器只接受带 `n08_` 名称、哈希匹配的试验 profile。#260 已通过的试验实际使用 `config/components/mapping/n08_low_speed_trial.json`（`max_velocity=0.10 m/s`、`max_acceleration=0.25 m/s²`、vector cap 0.12 m/s）。这不是测试速度不合格，而是启动命令漏传已验证配置。

运行未创建 `flight.json`，未启动 `run_n08_braking_trial.py`、未发任务目标、未解锁、未发布桥控制。PX4 实时读回 `arming_state=DISARMED`、`landed=true`；桥 `phase=DISABLED`、`control_enabled=false`。`bash tools/project.sh stop n08-20261025-263-yaw-first-return` 退出码 0，项目容器已停止。

## 下一步

不能在已用默认 profile 启动的实例里改写 manifest 或替换 EGO 参数。#264 使用全新 run，明确设置 `D435I_PLANNER_CONFIG=config/components/mapping/n08_low_speed_trial.json`，并重做 N05 支架扫描以获得新 epoch 与新鲜地图。扫描前先核对 launch manifest 确认 planner path、hash、max velocity 和 max acceleration 正确；若不匹配就停在 DISARMED 阶段。只有此后支架释放、post-release N05、mission 当前区 N05 和 40 秒 preflight 均通过，才执行前向制动／原地 180° yaw／前向返航。

完整原始目录：`artifacts/runs/n08-20261025-263-yaw-first-return/` 与 `artifacts/runs/n08-20261025-263-yaw-first-return-stack/`。N08 保持 `in_progress`；本轮是 profile 准入失败，不构成速度、转向或返航飞行结果。
