# N09 contact instrumentation and live refusal (#329)

对话摘要：[2026-10-26-329 N09 接触观测](../../collaboration/dialogues/2026-10-26-329-n09-contact-observation.md)。父目标 N09 保持 `in_progress`；本记录不把启动检查计为飞行通过。

## 本次实现

- 新增 `tools/prepare_n09_contact_model.py`，从当前 PX4 x500_base 和项目 D435i 模型生成 run-local overlay，只在 base_link、4 个 rotor link、D435i link 上添加 Gazebo Contact sensors；没有改 link pose、碰撞体或控制输入。清单记录所有源模型资源及生成模型哈希。
- `tools/sim_runtime.sh` 用 `D435I_N09_CONTACTS=1` 启用此 overlay；PX4 server config 已包含 `gz::sim::systems::Contact` 插件。
- 新增 `tools/record_n09_contacts.py` 只读记录 6 个话题和每个碰撞对；传感器话题未全部出现时 N09 runner 在起飞前拒绝。
- 新增 `tools/run_n09_live_refusal.py`，真实 action server 对地图外目标执行当前地图球查询，必须报告 `map_query_outside_map`、不向 EGO 转发且 PX4 bridge 仍 DISABLED／未解锁／着地。
- `tools/evaluate_n09_mission.py` 按任务阶段区分允许的起飞前及着陆地面接触与禁止的飞行期地面／障碍物接触，并纳入 live refusal 结果。
- `tools/project.sh` 透传 N09 contact 模式；`tools/n09_runtime.sh` 核对运行时传感器模型和世界 Contact plugin，执行 live refusal，并改用容器内可用的 `grep` 做旧 goal topic 订阅检查。修复提前退出时观察进程的清理。
- `docs/n09-completion-test-plan.md` 更正 action 命令坐标为 odom 绝对值，补入 live refusal 与接触判据。

## 验证

- N09 contact overlay 单测：6 项通过；生成模型对 base、四个 rotor 和 D435i link 覆盖完整。逐 collision XML 语义比较保持一致。
- `gz sdf -k`：生成的 x500_base 与 d435i 模型均 Valid；只看到现有上游 `gz_frame_id` SDF schema warning。
- `bash tools/project.sh test`：389 项 Python tests 通过，action 集成通过未知、occupied、越界、错误身份、过期与 timeout 查询拒绝；caller cancel、活动替换及旧 fault 隔离；3D+yaw 完成；stale epoch、clock regression、freshness 与 shutdown abort。
- `bash -n tools/project.sh tools/sim_runtime.sh tools/n09_runtime.sh`、Python compile 和 `git diff --check` 通过（修正相对路径及 `rg` 后需再次跑最终检查）。

## SITL 启动诊断

- `n09-20261026-pilot01`：PX4 build 准备后、Gazebo/PX4 启动前因脚本在 PX4 build cwd 使用相对 `tools/` 路径失败；未进入飞行控制，会话已退出。
- `n09-20261026-pilot02`：Gazebo/PX4 启动且 6 个 `/n09/contact/...` 话题全部出现。独立读回 `/uav_px4_bridge/status` 为 `DISABLED`, `armed=false`, `landed=true`；PX4 `vehicle_land_detected` 为 `landed=true`。为修正运行时脚本后保持同版本指纹，未继续调用 mission runner；通过 `project.sh stop` 安全退出，container exit 0。没有发送拒绝探针、flight goal 或 enable 请求。
- 两个目录都是工具/观测启动诊断，不是 N09 pilot、成功重复或 N11–N14 正式次数。当前仍未取得任何 N09 飞行结果。

## 下一步

用全新 run id，启动命令固定 `D435I_N08_MODE=execute D435I_N09_CONTACTS=1 D435I_PLANNER_CONFIG=config/components/mapping/n08_low_speed_trial.json`。先执行 fresh N05、真实地图外 action 拒绝、contact-topic readiness，再做一条候选 3D/yaw 航点。pilot 成功后，保持同一源码、配置、安装和 evaluator 身份完成 3 个独立 cold-start 成功任务；失败门禁保留 no-go 证据，不放宽准入。
