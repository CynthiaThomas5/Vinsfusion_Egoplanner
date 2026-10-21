# GOAL C A* 调整循环与局部池越界追踪（#311）

- 对话摘要：[ #060](../../collaboration/dialogues/2026-10-20-060-p2-ego-astar-callsite-diagnostics.md)。轻量证据：[A* callsite diagnostic](../evidence/p2-ego-astar-callsite-diagnostics-20261020-311.json)。
- 改动：新增 EGO 隔离 patch `0024-astar-input-diagnostics-experiment.patch`、来源／构建清单、run-local 无真值订阅的运动驱动副本和 planner-only harness；补充 `dependencies/patches/ego/README.md`、项目 CURRENT/README、GOAL checklist 证据引用。修正 #308 attempt 01 中将执行顺序与结果合写为字符串的字段。未修改 canonical EGO 源码、`dependencies/sources.json`、PX4 参数或里程碑状态。
- 构建：`patch --binary --dry-run -p1` 对 0024 预检副本通过；实际应用后两份 A* 源文件与候选副本逐字节一致。`bash artifacts/runs/p2-ego-astar-callsite-diagnostics-20261020-311/build-container.sh` 以 `d435i-vins:dev`、#297 underlay 构建 `traj_utils`、`plan_env`、`path_searching`、`bspline_opt`、`ego_planner`，5/5 通过。构建日志和二进制 SHA 写入 run-local build report。
- 运行：`bash artifacts/runs/p2-ego-astar-callsite-diagnostics-20261020-311/run-container.sh` 完成 planner-only 仿真。定位在 goal 前有效，MapStatus ready，同一 epoch/map_id 下探针收到3条 B-spline；运动驱动器发出8个力变化命令并采集6601个 IMU 样本。无 trajectory server、控制器、PX4、truth/control ROS topic或 snapshot service 调用。
- 结果：44,870次A* reject全部伴随起终点调整后池越界，其中38,348次start侧、6,522次end侧；没有一次原始start/end坐标的首次量化越界。按请求坐标和中点匹配blocked-cell与越界日志，43,149个失败起始格心为unknown且inflated，1,721个为known且inflated。代表调用在start格心未知后，将start向远离end方向移动61步，最终越出100³局部池。该机制证实于实验 patch 0020/0024，不代表 canonical EGO。
- 验证命令：patch dry-run/apply+`cmp`；5包 colcon build；两个 shell harness `bash -n`；run-local Python `py_compile`；后续结构检查、证据引用检查与 `git diff --check` 记录在本轮收尾验证。
- 局限与下一步：run-local inflation 0.5 m；callsite patch 的逐调整日志达106,725,459 bytes，可能扰动负载与时序。没有同刻地图快照、轨迹执行、净空测量或独立重复。先将日志限制到最终pool-exit与首个blocked cell；离线验证 known-free、unknown、inflated 三类起点在有限调整预算下可明确成功或fail-closed，再考虑是否值得提出 canonical 修复。
