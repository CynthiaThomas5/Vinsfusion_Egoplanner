# 修改与验证记录

- 任务 ID／日期：GOAL C EGO canonical dense-spline guard #326 / 2026-10-21。
- 对话摘要：[2026-10-21-001 对话摘要](../../collaboration/dialogues/2026-10-21-001-p2-ego-canonical-dense-spline-guard.md)。
- 修改文件：新增本记录、对话摘要和 [轻量证据](../evidence/p2-ego-dense-spline-canonical-unknown-guard-20261021-326.json)；更新 `progress/CURRENT.md`、`progress/goal-checklist.json`、`progress/evidence/README.md`、`dependencies/patches/ego/README.md`；运行分析器 `artifacts/runs/p2-ego-dense-spline-canonical-unknown-guard-20261021-326/analyze_spline_snapshot.py` 增加 planner 首 2/3 检查时域与末尾 1/3 的独立统计。未修改 `src/vendor/ego_planner`、`dependencies/sources.json` 或里程碑状态。
- 行为变化及原因：#326 以 pinned upstream `23a8d5a191711dd65633df689bd00f55d4dea8f9` 加 15 个 canonical patches 重建，再叠加隔离实验 0029/0030/0031。5 包 Jazzy Release 构建通过。23.23 秒 planner-only 仿真收到 2 条 B-spline 和 2 份只读占据快照；运行图中真值 topic、控制 topic 和控制节点均为空。10,331 条 dense-check 拒绝样本均为 in-map unknown（raw=0、inflated=0）。两条曲线在初始 2/3 guard 时域内都无 blocked sample；第一条完整曲线的末尾时域有 2 个 inflation-mask hit，最近 raw occupied voxel-box 净距 0.49993 m，即 nominal 0.482 m 球体外仅 0.01793 m；第二条无 inflation hit，净距 0.60746 m。
- 验证类型：源码重建／静态来源审计、Jazzy Release 编译、Gazebo live planner-only 仿真、只读离线体素分析；非 PX4 SITL／实机验收。
- 命令与环境：在 `d435i-vins:dev` ROS Jazzy 环境构建 `ego_planner` overlay；`bash artifacts/runs/p2-ego-dense-spline-canonical-unknown-guard-20261021-326/run-container-snapshot.sh`；`python3 artifacts/runs/p2-ego-dense-spline-canonical-unknown-guard-20261021-326/analyze_spline_snapshot.py`。运行摘要、构建日志、二进制与快照 SHA-256 见对应轻量证据及 `artifacts/runs/p2-ego-dense-spline-canonical-unknown-guard-20261021-326/`。
- 结果及证据位置：见 [#326 轻量验收报告](../evidence/p2-ego-dense-spline-canonical-unknown-guard-20261021-326.json)。`python3 tools/project_status.py` 返回 `Structure/design check: PASS`；goal checklist、证据报告与分析 JSON 解析通过；分析脚本 AST 语法检查通过；`git diff --check` 通过。结构检查只代表骨架一致，不代表 P0–P6 或 GOAL C 验收。
- 未验证与 PROVISIONAL：地图已知覆盖率仅 0.50%/0.60%；截图请求分别晚于 spline start 4/69 ms，源深度龄 136/99 ms；0.5 m 轴对齐 cube inflation 仍为 run-local 实验。18 mm 名义余量低于既有约 7 cm 地图几何 P95 量级，尚无机体扫掠、轨迹跟踪/制动、PX4 控制、路径执行或真值评估。GOAL C/D/F 和 GOAL A–H 总体验收保持 pending；健康与安全阈值不冻结。
- 下一步：在 canonical #297 重建基线上联合复测 patch 0028 retry cooldown 与 0029–0031 unknown/inflation guard，保留 planner-only 隔离和逐 spline 快照；随后继续地图覆盖/几何及扫掠体/跟踪误差验收。

未提交；本仓库当前已有用户工作树修改，本轮没有暂存或提交。
