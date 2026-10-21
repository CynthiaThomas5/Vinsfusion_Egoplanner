# 修改与验证记录

- 任务 ID／日期：GOAL C canonical full-active-spline guard 诊断 #328 / 2026-10-21。
- 对话摘要：[2026-10-21-003 对话摘要](../../collaboration/dialogues/2026-10-21-003-p2-ego-full-active-spline-guard.md)。
- 修改文件：新增实验补丁 `dependencies/patches/ego/0032-full-active-spline-guard-experiment.patch`，只在隔离 #297 canonical reconstruction 上使用；新增 #328 运行记录、[轻量证据](../evidence/p2-ego-dense-spline-canonical-full-spline-guard-20261021-328.json)、本记录及对话摘要；更新 patch README、证据 README、GOAL C checklist 与 `progress/CURRENT.md`。未改动 `src/vendor/ego_planner`、`dependencies/sources.json` 或 milestones。
- 行为变化及原因：0032取消最终样条碰撞门的 2/3 截断，仍以10 ms采样并要求 in-map、known、raw-free、inflation-free。隔离 Jazzy Release 构建5包通过。Planner-only 45.001秒运行发出目标但没有 B-spline；439条最终样条拒绝中438条是在 t=0 附近的 in-map unknown 样点（raw=0、inflated=0），另有1条在 t=4.530秒命中 inflation mask（xyz=2.500726, 1.042540, 1.137918）。后者说明全活动区间检查拦截了尾段碰撞候选；因没有样条，probe没有请求配对地图快照。
- 验证类型：patch dry-run、五包 Jazzy Release build、Gazebo D435i/VINS/map/EGO planner-only live run、最终 ROS graph 静态检查。没有 PX4 SITL 或实机验证。
- 命令与环境：`patch --dry-run -p1 < dependencies/patches/ego/0032-full-active-spline-guard-experiment.patch`；`bash artifacts/runs/p2-ego-dense-spline-canonical-full-spline-guard-20261021-328/build-ego.sh`；运行脚本与输入均保存在 `artifacts/runs/p2-ego-dense-spline-canonical-full-spline-guard-20261021-328/`。构建5包完成（2分12秒）；运行45.000743秒，goal发送成功，B-spline与snapshot各为0；运行图无控制节点、控制话题或真值话题。
- 结果及证据位置：见 [#328 轻量证据](../evidence/p2-ego-dense-spline-canonical-full-spline-guard-20261021-328.json)、[源码清单](../../artifacts/runs/p2-ego-dense-spline-canonical-full-spline-guard-20261021-328/source-manifest.json)、[构建日志](../../artifacts/runs/p2-ego-dense-spline-canonical-full-spline-guard-20261021-328/build-ego.log)、[EGO日志](../../artifacts/runs/p2-ego-dense-spline-canonical-full-spline-guard-20261021-328/ego-01.log)及运行摘要。0032 SHA-256 为 `d455c372bcb8276f4f81a64f4b08e1605da833ca965f69f1b137182de481f19f`；隔离源码树SHA-256为 `09e1ccae79b08279ab55e6fbd1ee550ec4267dda955de51420f1aca392feaad4`。
- 未验证与 PROVISIONAL：虽然目标时 map ready 且超时时 mapping ready、localization valid，但 EGO仍记录57条 `odom or depth lost` 警告；没有同刻occupancy snapshot，无法确认t=0 unknown的持续时间或将零样条单独归因于0032。地图覆盖、vehicle-sweep、跟踪与制动距离、控制执行、PX4及真值评估均未覆盖；0.5 m inflation及0.482 m球半径未冻结。GOAL C和整体A–H继续pending。
- 下一步：扩展 run-local probe，在第一次 final-spline guard rejection时即使没有B-spline也捕获同 epoch occupancy snapshot，再重复固定场景；分别量化近原点unknown和后段inflation命中，保持fail-closed和1.0秒retry cooldown。

未提交；保留工作树中已有用户修改，本轮无暂存或提交。
