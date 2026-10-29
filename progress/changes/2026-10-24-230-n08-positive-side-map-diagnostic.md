# N08.2t #230：目标侧水平观察与失败态同图捕获

## 假设与唯一物理变量

- #229 same-identity N05 snapshot 的目标 terminal-hold unknown 集中在目标 +Y 一侧；EGO 对 36 个完整曲线查询以 unknown 拒绝。缺少 action-time raw map，无法确认任务失败时的 exact query volume。
- 唯一物理实验变量：在 #228 overhead 支架 profile 后增加 +π/2 水平观察并回中；不添加 −π/2 水平视角，不做两侧连续转动。保留 overhead 场景、其它支架段、N05/定位门、阈值和运动配置。
- 只读工具改动不是物理实验变量：若 goal 与 runner failure 已记录但无 B-spline，仍从相同 goal epoch/map 获取 raw snapshot，服务只读、不发目标或控制。

## 改动

- `config/components/simulation/preflight_scan.json` 增加 19 阶段 `n08_overhead_positive_side_view_profile`；前 12 阶段与 #228 overhead profile 相同，加入 +π/2 水平停留，回中后沿原路线返回。
- `tools/probe_preflight_scan.py`、`tools/run_n05_preflight_layout.sh` 注册新 profile。
- `tools/diagnostics/capture_n08_curve_map.py` 在 goal 失败、未生成 spline 时记录 runner failure，并仍检查同身份 `MapStatus`、有界重试 raw snapshot、保存 NPZ；成功生成 spline 的原路径不变。失败态 capture 仍是诊断证据，不会让 compute-only evaluator 通过。

## 验证与限制

- 代码静态验证：JSON 解析、相关 Python AST、profile 序列断言、shell `bash -n`、`git diff --check`、`python3 tools/project_status.py`。project status 只校验结构，不代替 ROS build 或 SITL。
- 本项运行只允许 N05 DISARMED 支架扫描、fresh online/offline gate、compute-only 和只读地图查询。若 N05/定位/地图拒绝，保留拒绝并按流程 landed/disarmed 后 stop；不执行 XY，停止包络仍未证明。
- 成功判据：profile 完整并 detach；post-release/current-area gates 同 epoch/map 接受；定位健康；目标 hold/body 与连续 sweep 在本 run map 上重算；若 EGO 在 READY 前拒绝，同 run failure map 已保存且与目标身份匹配。

## #230 实际结果

- Run `n08-20261024-230-positive-side-view-01` 完成 19/19 stages；fixture helper 的 `localization changed or became invalid during physical scan` 错误保留。独立记录确认 fixture 已 detach/remove、车辆 landed。
- Post-release/current-area N05 online/offline gates 同 epoch/map 接受。40.003 s preflight 通过；source timeline 806/806 LocalizationStatus valid、175/175 MapStatus ready。
- Compute-only 在 B-spline 前 `planner_full_curve_unknown` 中止。新 observer 在 failure 状态抓到同 goal、epoch、map 的 raw snapshot；goal stamp 与 snapshot 相差 6.068 s，故报告为拒绝后的同身份快照，不声称精确 action-time snapshot。
- Production-mirror raw 查询：推断起点 body free、hold sphere 有 309 unknown；目标 body free、terminal-hold 有 42 unknown；连续直线 cover sweep 首次查询含 6 unknown。unknown 在地面以上。未产生 READY、PX4 PositionCommand、水平位移或制动测量；最终 landed/disarmed，容器 stop exit 0。
- N08 stop envelope 仍未证明。曾筛到释放点 +Y 0.30 m 候选，随后检查确认 N05 fixture 只有 x/z/yaw/pitch 轴，没有 y 轴，故不将该不可实施候选作为下一步。当前 #231 使用同一释放点和 `[+0.10,+0.25,0] m` 目标 offset；#230 旧图上 path、目标 hold、目标后 0.50 m swept corridor 与 stop hold 查询均 free，但 start hold 仍有 309 unknown。仅待 fresh N05 / compute-only 复核，不授权 XY。
- 证据：[报告](../evidence/n08-positive-side-map-diagnostic-20261024-230.md)、[结构化记录](../evidence/n08-positive-side-map-diagnostic-20261024-230.json)。

对话摘要：[dialogue](../../collaboration/dialogues/2026-10-24-230-n08-positive-side-map-diagnostic.md)。
