# N08.2s #229：单侧后方水平观察诊断

## 假设与唯一变量

- #228 的 post-release/current-area 地图仍有起点 hold unknown。沿用 overhead 支架 profile，只增加 yaw=−π/2 观察并回中，不做第二侧 +π/2，测试该单侧视角是否能减小 unknown。
- 保持 overhead 布局、其余支架阶段、相机 pitch、健康门限、N05 判据、EGO 和 PX4 配置不变。

## 实际运行

- 新 profile `n08_overhead_rear_one_side_view` 完成 19/19 stages。before gate 拒绝地面 raw occupied voxel 数不足；扫描后 after/post-release/current-area N05 online/offline 都接受且同 epoch/map。
- helper 报 localization 在物理扫描期间变化，退出 1；错误保留。stage 完成、fixture detach/model absent、车辆最终 landed/disarmed 均有独立读回。
- mission preflight 通过。定位 observer 754/754 status valid，没有复现 stale；MapStatus 164/164 ready，但最大 source-stamp gap 428 ms，保留为观察，不改门限。
- compute-only 目标在 EGO 发布 READY 曲线前因 `planner_full_curve_unknown` 中止。planner 记录完整曲线 36 queries、reason unknown；无水平轨迹到桥，PX4 landed/disarmed。专用 evaluator 未通过，不能记为 READY/cancel/hold 子项通过。
- 从同身份 N05 pre-action raw map 用 production-mirror 查询复算：start hold unknown 209、target terminal-hold unknown 254、末端直线 sweep query 22 因 6 unknown 拒绝。unknown 中心位于地面 plane 以上。action-time map 未捕获，因此这些查询定位了持续存在的风险区域，但不等同于 EGO 当时逐 query 的原图。

## 代码／配置变更与验证

- 新增显式 `n08_overhead_rear_one_side_view_profile`，profile allowlist 在 probe 与 shell runner 同步更新。
- `python3 -m json.tool config/components/simulation/preflight_scan.json`、相关 Python AST 解析、19-stage yaw 序列断言、`bash -n tools/run_n05_preflight_layout.sh`、`python3 tools/project_status.py` 和 `git diff --check` 均通过。结构检查不是 ROS build 或 SITL 证据。
- 运行命令：`N05_KEEP_SIM=1 D435I_N08_MODE=compute_only D435I_PLANNER_CONFIG=config/components/mapping/n08_low_speed_vector_cap.json bash tools/run_n05_preflight_layout.sh n08-20261024-229-one-sided-rear-view-01 n08_overhead_calibration n08_overhead_rear_one_side_view`；随后 `D435I_N08_MODE=compute_only D435I_PLANNER_CONFIG=config/components/mapping/n08_low_speed_vector_cap.json bash tools/project.sh mission n08-20261024-229-one-sided-rear-view-01 config/components/navigation/n08_compute_only_fresh_map_goal.json`。mission 因预期安全拒绝返回 2；flight/evaluator/report 原样保留。
- 独立 bridge status readback：`phase=LANDED`、`control_enabled=false`、`armed=false`、`landed=true`。`bash tools/project.sh stop n08-20261024-229-one-sided-rear-view-01` 返回 0；容器状态 exit 0。

完整结果、空间查询和 SHA-256 见 [#229 evidence](../evidence/n08-one-sided-rear-view-20261024-229.md) 与 JSON。

## 下一项

N08.2t #230 直接观察目标 terminal-hold 的 +Y 侧：在相同 overhead profile 上只增加 +π/2 水平视角后回中，不做 −π/2 侧视。另让只读 map observer 在已匹配 goal 但 runner 因 no-curve 失败后，仍捕获同 epoch/map raw occupancy；此 observer 不发命令，不改变实验。全部 N05/定位门限不变，仍不执行 XY。
