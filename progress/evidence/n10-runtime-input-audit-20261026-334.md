# N10.1 运行输入与版本审计（#334）

**结果：N10.1 静态输入与启动链审计完成；N10 整体仍在进行。** 这份审计固定了本轮开始时的代码候选快照，追踪了锁定源、当前安装指纹及 N09 的实际启动参数。重建后节点参数和 ROS graph 仍要在 N10.6 再读一次。

## 候选身份与依赖

- Git 基线 `fd90f3b73e48101ad35c5a0ed9372865392eca7c`，开始审计时工作区有 1022 个已修改／未跟踪状态项。它们没有回滚；源码快照取当时实际工作区字节，不只取 HEAD。
- [候选代码快照](../../artifacts/runs/n10-20261026-334-audit/snapshot-initial/project-source.tar.gz)：2112 个受管源码／配置／文档文件；SHA256 `405cffd0e0b0e8892bc4769f73932864da54c4fef524254e21e3b54a18460de5`。文件清单在同目录 `manifest.json`。
- 当时 `runtime_manifest.py` 得到 645 个输入／安装条目的指纹 `6b95d5fe48ea17f41649947547ccab4bf0798e9907a565dbb2dfd65cf0579f30`，与 N09 #332 三次成功 run 使用身份一致。审计后仅元数据／说明文字已作修正，最终 N10 身份将在后续收敛后重算。
- Docker 本机 `d435i-vins:dev` 的 image ID 与 `config/runtime.json` 完全一致：`sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`。锁文件记录的 1.49 GB portable archive 未位于原路径，故标准全量 export 按设计拒绝；先生成了 code-only 快照。N10.7 前必须生成并锁定可交付镜像归档。
- 固定补丁文件哈希 `48/48` 通过，VINS/EGO 当前裁剪源码的补丁后文件哈希 `25/25` 通过。EGO 锁中列的是上游 `src/planner/...` 路径，审计按 `package_roots` 对照当前 `planner/...` 目录。
- PX4 HEAD 与锁定 revision 相同（`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`）；递归子模块 `39/39` 均在锁定 gitlink，无未初始化或不匹配项。原锁指向的旧清单缺失，本轮从当前 checkout 重建为 [`px4-submodules.json`](../../artifacts/runs/n10-20261026-334-audit/px4-submodules.json)，更新 `dependencies/sources.json` 指向新清单并保存哈希。

## 实际入口与生效参数

| 入口 | 实际配置 | 已核对的要点 |
| --- | --- | --- |
| `project.sh sim` / 普通 16 m mission | 默认 `config/components/mapping/ego_planner.json` + `room_crossing_goal.json` | planner 逐轴上限 0.5 m/s、加速度 0.8 m/s²；目标 16 m；native dwell 1 s；action timeout 为 180 仿真秒，client 的 wall wait 是 184 秒，低 RTF 时可能提前取消；独立的 75 s CLI 值只等待 takeoff 后进入 ACTIVE。 |
| N09 PX4 mission | `n08_low_speed_trial.json` + `n09_3d_waypoint_goal.json` | 0.1 m/s、0.25 m/s²；+0.4 m / +0.1 m / +0.2 rad；native dwell 1 s。三次通过 run 的 launch manifest 与当前配置解析器输出逐项相符。 |
| 全链碰撞与控制 | `task_supervisor.json`、VIO/EGO launch、唯一桥接节点 | `official_ego`；保持 raw unknown 分类，规划侧用 inflated occupied；独立垂直起飞后才转发导航目标；PX4 控制消息由 `uav_px4_bridge` 独占，truth 只供离线评估。 |

GOAL F 默认要求位置误差 ≤0.30 m、yaw ≤15°、连续满足 ≥3 s；现有两个活动 goal profile 的 native dwell 都只有 1 s，需在 N10.4 让任务保持与独立判断统一。README 的默认 16 m 入口也走了未经 N08/N09 低速实测的 0.5 m/s profile，且实际 timeout 与 profile 不一致；N10.2/3 决定证据适用范围，N10.4/6 修正并验证入口。`minimum_occupancy_points` 在当前源码中没有消费者；official_ego 分支不将其作为起飞或目标前置。已从活动 policy rationale 清掉“unknown 与 occupied 都阻断”的过期说法；依赖补丁顺序与 N09 状态说明也已同步。

## 本轮记录与验证

- 代码快照：`python3 tools/export_project.py ... --code-only`，2112 文件成功；全量 export 因锁定镜像归档缺失按预期 fail-closed。
- 当前安装指纹：`python3 tools/runtime_manifest.py artifacts/runs/n10-20261026-334-audit/runtime-manifest-initial.json`；与 #332 N09 SHA256 一致。
- 来源校验：48 个补丁哈希、25 个当前第三方修补文件哈希通过；PX4 revision、39 个 recursive submodule gitlink 与重建清单通过。
- 配置解析：当前 resolver 输出与 N09 repeat01/02/04 的 launch manifest 匹配；未将历史 manifest 当成新安装的 live node 参数回读。

**未解项／下一步**：图像归档需在 N10.7 重新打包；默认 16 m planner 与 runner timeout、1 s dwell 进入 N10.2 风险表和 N10.4 修复。现有 runtime manifest 未覆盖实际 vendor 补丁、所有安装 share/launch 和完整 PX4 来源；最终清单工具需在 N10.4/7 补齐。下一子项 N10.2：将 N01–N09 证据映射到 GOAL A/F 及 N11–N16 需要的距离、时长、运动和故障范围。
