# gpu4090 Codex 测试交接（2026-10-22）

## 给接手 Codex 的第一条指令

先读本文件、AGENTS.md、README.md、GOAL.md、progress/CURRENT.md、progress/milestones.json，先执行 `git status --short --branch`。工作树有大量本任务历史未提交修改，全部保留；不要 reset、clean、重新 clone 后覆盖，也不要直接 git pull 覆盖现场。用户要在服务器继续测试，本轮仅交接，没有提交或推送。

**项目还没有达到当前版本“完整可飞”。用户最关心的是 VINS 里程计可靠性及后续迁移 Nano。前任把范围扩到了地图和轨迹安全，耗时过长；接手后收尾现有实验，再优先解释和修复 VINS 残差越线，不继续无边界扩展工程。**

## 位置与环境

- 服务器项目：`~/D435i-VINS-EGO-ROS2`。原工作端 SSH 别名 `gpu4090`；在服务器本机直接操作，不依赖这个 SSH 别名存在。
- 原工作端副本：`/home/ac/codexworkspace/PX4_ROS2/D435i-VINS-EGO-ROS2`。不是服务器路径。
- Ubuntu 24.04、ROS 2 Jazzy、Gazebo Harmonic、PX4 v1.17.0、双 RTX4090。服务器没有 rg 时用 grep/python。
- 固定镜像 `d435i-vins:dev`，ID `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`。
- 容器工作目录 `/workspace`，绑定服务器仓库；默认 install 为唯一集成构建。仿真 ROS domain 84、Gazebo partition 按 run 隔离。隔离 ROS 测试不能连接在运行仿真的 domain。
- Jetson Nano 4GB、Ubuntu20.04/L4T32.7.6、ROS Foxy，目前只做过只读盘点。没有修改真实设备或进行真机飞行。

## 刚核实的运行现场

交接时运行容器：`d435i-flight-safety-20261022-065-coverage-01`。

运行目录：`artifacts/runs/flight-safety-20261022-065-coverage-01/`。

`fixture-result.json` 已存在：

- outcome `unarmed_support_coverage_completed`，error 空；profile `coverage`。
- epoch `ee4e06fb07304bb9ae879eaaa04faf98`，最终 localization valid，reason `fresh_inputs_and_usable_solver`，normalized_cost `0.8338860067382783`。
- VehicleStatus 400 个样本，仅状态 1（DISARMED）。无解锁、无导航目标、无飞行。
- 支架状态 attached → detached，`fixture_may_remain_attached=false`。工具成功路径还请求移除支架，但接手应检查日志，不能仅凭字段认定所有资源均已清理。
- result 的 scope 文本仍写 smoke，是工具描述不够准确；实际 profile 和 outcome 是 coverage。这里的 completed 只表示动作流程结束，**没有证明地图足够覆盖**。
- final_joint_states 是支架关节数据，不是机体真值，不据此宣称厘米级定位误差。

其他运行容器 `volant-height-route-probe`、`natfrp-service` 与本任务无关，不停止或修改。

先确认现场：

```bash
cd ~/D435i-VINS-EGO-ROS2
git status --short --branch
docker ps --format '{{.Names}} {{.Status}}'
cat artifacts/runs/flight-safety-20261022-065-coverage-01/fixture-result.json
```

若仍运行，可先只读保存扫描后的地图快照；这是收尾，不需要再次扫描或飞行：

```bash
mkdir -p artifacts/runs/flight-safety-20261022-065-coverage-01/map-after-scan
docker exec d435i-flight-safety-20261022-065-coverage-01 bash -c 'source /opt/ros/jazzy/setup.bash; source install/local_setup.bash; python3 artifacts/runs/flight-safety-20261022-063-checks/capture_grid.py /workspace/artifacts/runs/flight-safety-20261022-065-coverage-01/map-after-scan'
```

该 capture 工具在 artifacts 中，先确认文件存在；会等地图就绪并写 raw-grid.npz/json。失败如实记录，不填充未知、不反复扩展扫描。随后停止本任务已确认 DISARMED 的仿真：

```bash
bash tools/project.sh stop flight-safety-20261022-065-coverage-01
```

交接本身没有执行这个 stop。先检查当前状态，避免按过时快照操作。

## 原始故障与应优先继续的分析

### 已知事实

1. #057 原始 VINS 的16m基线：单一起飞前 SE3 对齐、尺度1；85.144仿真秒、1290对，位置 RMSE 4.56cm、最大9.01cm、最后8.77cm，yaw RMSE 0.294°。有累计误差，不是已经严重发散，也不能外推真机。
2. #058 已接独立 loop_fusion 观察后端、稀疏点及位姿图；67关键帧，但实际 verified loops=0、优化=0。**展示图不等于消漂**，后端没有反馈到控制。
3. #059 第二轮去程16m与驻留通过，返程2.704仿真秒后 normalized_cost=1.00369195 超过原阈值1.0，取消任务、落地上锁。该帧位置误差9.13cm，实际 yaw 仅约变化−9.14°，不能称180°急转导致。总代价486.801→1092.019，残差分量数2036→2168；原触发缺少分组代价，根因未定。
4. #060 两轮另有机制：总代价略降，残差分量数下降使归一化指标越线；先验占比约90%/80%。第一轮 C1850.6215→1828.6738，N3878→3442，q .9769445→1.0308078；第二轮 C1532.1258→1526.4833，N3132→2894，q .989125→1.027098。触发帧位置误差8.93/7.23cm。不能把该机制直接套到 #059，也不能据此认定健康门误报。
5. startup telemetry_stale、先验累积机制、质量判据是否经过独立校准、真实回环修正均未解决。

入口证据：

- `progress/evidence/vio-drift-baseline-20261022-057.md`
- `progress/evidence/loop-observer-20261022-058.md`
- `progress/evidence/loop-revisit-20261022-059.md`
- `progress/evidence/vio-residual-20261022-060.md` 及对应 JSON、原始 run。
- `tools/debug_truth/evaluate_residual_transition.py`、`evaluate_odometry.py`。
- #065 的 fixture-vins.jsonl、fixture-odometry.jsonl、fixture-trace.jsonl 可作为新的不解锁观测；不能伪造 flight.json 使评估器通过。关节 trace 没有精确源时间，不拿它做高精度真值。

### 建议下一个小目标

先输出 #059 与 #060 首次越线前后的对齐表，区分总代价、分量数、先验/视觉/IMU、特征寿命、运动及独立位姿误差，列出哪些已有数据能回答、哪些必须补采。确定一个可证伪的根因假设，做一次有界受控实验。若新飞行安全前提不成立，先做回放/不解锁实验，不恢复旧危险路线。不要一上来调高阈值、加等待或同时改多个算法。

## 地图／安全方面已实施的内容（不是飞行验收）

### #061–062

发现旧 `config/components/navigation/room_loop_goal.json` 的4m返回点落在柱体内，现保持 `enabled:false`。#060 两次完整机体净空为−0.132/−0.201m；落地上锁不能称安全飞行通过。13m候选仅离线几何分析，不是可直接启用的回环路线。

目标转发前调用实际 EGO raw 体素球服务 `QueryOccupancySphere`；绑定 epoch/map_id/frame、源和融合新鲜度，unknown/occupied/outside/timeout 拒绝。0.5m 球只是现有标称试验包络，没有校准定位、跟踪、延迟、制动预算。

### #063

EGO 补丁 `0038-complete-depth-rays.patch` 修复射线格坐标、跨格、提前截断、重复端点和每帧投票去重；250条确定性射线对照错/漏格287→0。构建17包、183回归＋ROS action、fresh fetch53文件一致。

两次静态不解锁快照 free10506/14252（不同冷启动，非严格AB）。修复后最大非free格中心距离约0.4472m，加保守上界后0.4838m仍小于0.5m，说明该固定快照没有完整0.5m free球，并非所有未来地图都不可能。

报告 `progress/evidence/depth-rays-20261022-063.json`、对应 changes；原始数据在 `flight-safety-20261022-063-map-01/02`。

### #064

EGO 补丁 `0039-full-curve-admission.patch`：基于样条导数控制点速度上界，把分段中点球扩张以覆盖整段，检查全活动曲线、剩余曲线、完成后 hold；unknown/occupied/outside/资源限额均拒绝。规划失败锁止并发布 `/navigation/planner_fault`，navigation 按 goal/epoch 清理活动和已完成 hold。

`NavigationCommand.msg` 新增 map_id。独立球/快照查询仍拒绝 pending depth；内部检查在串行回调读取上次完整融合，原 .4s 源/融合龄门不变。以后若改多线程须重新审查锁。

自身 node 查询只在原 .25墙钟秒总期限内对 no_fresh_fused_depth/occupancy_update_stale/depth_source_stale 重试；不重试 unknown/occupied/身份错，不延长期限。该修改发生于 #065 启动后，运行节点载入的是此前版本，不能继承当前源码整机飞行资格。

验证：17包；最新187项回归＋ROS action通过；fresh fetch54文件一致。真实安装 EGO 的隔离合成组件试验 component-01/02 通过：实际查询 free/occupied/unknown/outside、wrong map拒绝、活动曲线及完成后 hold 障碍故障停止、故障后晚发曲线0。合成组件没有PX4/VINS/飞行，不能替代SITL。

证据文件 `progress/evidence/full-curve-20261022-064.json` 和 changes **尚停留184项/component-01，需按原始日志补齐，不直接把交接文字当通过证据**：

- `artifacts/runs/flight-safety-20261022-064-build-fusion-wait.log`
- `artifacts/runs/flight-safety-20261022-064-tests-fusion-wait.log`
- `artifacts/runs/flight-safety-20261022-064-component-02/result.json`
- `...-064-component-01/result.json`

### #065 未武装扫描支架

文件：`simulation/models/preflight_scan_fixture/`、`config/components/simulation/preflight_scan.json`、`tools/probe_preflight_scan.py`、`tools/test_preflight_scan.py`。

只通过 Gazebo 原生关节力/PID 支撑并移动整个真实仿真机体，包含相机/IMU；没有移动独立相机、没有真值定位回馈、没有ROS控制/目标发布。smoke01和coverage01成功仅说明整机支撑动作与同会话跟踪完成。覆盖结果尚未评估。

曾询问用户是否接受真机解锁前手持整机扫描，**尚未得到答复**。这不是已批准的日常真机流程，不把支架当正式起飞方案。默认 launch 不加载支架。支架未脱离时禁止解锁。

## 当前潜在问题与禁止误判

- GridMap 空投影帧可能仍刷新 has_fused_depth/source/update 时间，是代码审查发现的潜在问题，**未实现修复、没有0040补丁、没有验证结论**。若接手处理，单独定义复现和范围，不再借此无限扩展。
- 起降地面接触、自身区域、起飞盲区、误差/制动预算、失效降落净空未验收。房间无天花板，远墙超深度范围会留下真实 unknown；不能凭空清空。
- #063–065 未修复 VINS 残差机制，未证明任何真实回环优化，未验证 Nano 算力/内存可用性。
- 默认16m演示是历史通过；新 gate/new build 不能继承飞行资格。P4–P6 仍进行中，A–H 最终验收未完成。
- VINS 锁定提交72023bc5d2abb14faa4c02a5c040d84f996b587a，当前二进制 SHA256 `1f878b2dabe2610e7b56eb65db18df4cd6bebf26891827a7b15cb1c551a7dfba`；0017只读代价观测，没有改求解/健康阈值。连续观测用 `VINS_DIAGNOSTIC_COST_GROUPS=continuous`，默认首次越线观测，记录开销。
- EGO 锁定提交23a8d5a191711dd65633df689bd00f55d4dea8f9；0037/38/39按 sources.json 顺序应用。vendor通常被忽略，不能只复制Git已跟踪文件就声称现场完整。

## 常用命令与交付纪律

```bash
bash tools/project.sh build ros
bash tools/project.sh test
python3 tools/project_status.py
git diff --check
```

`bash tools/project.sh sim RUN_ID` 仅启动新仿真，不解锁；`mission`/`./start.sh fly` 会进行真实 SITL 飞行，安全前置未满足不要盲跑。新实验先确认只运行一套本项目仿真，使用新run/epoch，不复用故障会话。

所有PX4设定点、OffboardControlMode由 uav_px4_bridge 独占。在线不用真值或完整世界地图，debug_truth只读隔离。不得放宽健康门、重写源戳、把未知当free、隐式拼接epoch或丢弃失败结果。

先保留065结果和地图结论，补充065 change/evidence、更新064证据及必要 contracts/running 文档。保持 CURRENT 简洁，里程碑只能凭实际证据更新。对话摘要不是测试证据。未获明确要求不提交/推送、不修改Nano。
