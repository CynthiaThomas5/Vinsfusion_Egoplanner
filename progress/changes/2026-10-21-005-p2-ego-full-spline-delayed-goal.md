# 修改与验证记录

- 任务 ID／日期：GOAL C 延迟目标派发与 full-spline unknown 起点诊断 #330 / 2026-10-21。
- 对话摘要：[2026-10-21-005 对话摘要](../../collaboration/dialogues/2026-10-21-005-p2-ego-full-spline-delayed-goal.md)。
- 修改文件：仅新增 run-local `artifacts/runs/p2-ego-full-spline-guard-delayed-goal-20261021-330/`；新增 [#330 轻量证据](../evidence/p2-ego-full-spline-guard-delayed-goal-20261021-330.json)、本记录与对话摘要；更新 GOAL C checklist、证据 README 与 CURRENT。复用#328 planner binary及#329 snapshot observer；未改第三方源码、canonical依赖清单或控制链。
- 行为变化及原因：将目标派发前连续ready窗口由0.5秒延至25秒，保留13秒仿真运动初始hold与相同目标、障碍及1.0秒重试cooldown；probe观察窗延长至75秒。Goal于仿真stamp22.012秒发送，此前已发生4次传感器force phase变化。75.021秒后无B-spline；425次 final guard拒绝全为in-map unknown/raw-free/not-inflated，其中367次首拒绝在t=0，另58次首阻样点延续至t=1.59秒。起点拒绝后48 ms获取的同epoch/map_id快照显示该样点cell仍unknown、inflation=0，3×3×3邻域13 free/14 unknown，无occupied/inflated。Known coverage为0.617%，且本轮无odom/depth lost警告。
- 验证类型：run-local Python语法、shell语法；复用#328同一Release binary的Gazebo D435i/VINS/mapping/EGO planner-only运行；同epoch只读快照与离线体素分析。未执行轨迹，非PX4 SITL／实机验证。
- 命令与环境：`python3 -m py_compile .../probe_ego_goal_with_snapshot.py .../analyze_guard_snapshot.py`；`bash -n .../run-live-with-snapshot.sh .../run-container-snapshot.sh`；`bash .../run-container-snapshot.sh`；`python3 .../analyze_guard_snapshot.py --result .../planner-goal-result-01.json --snapshot .../snapshots-01/guard-first-reject-occupancy.npz --output .../guard-snapshot-analysis-01.json`。ROS domain186；无控制节点、控制话题或真值话题。
- 结果及证据位置：见 [#330 轻量证据](../evidence/p2-ego-full-spline-guard-delayed-goal-20261021-330.json)、[run manifest](../../artifacts/runs/p2-ego-full-spline-guard-delayed-goal-20261021-330/run-manifest.json)、[目标结果](../../artifacts/runs/p2-ego-full-spline-guard-delayed-goal-20261021-330/planner-goal-result-01.json)、[snapshot archive](../../artifacts/runs/p2-ego-full-spline-guard-delayed-goal-20261021-330/snapshots-01/guard-first-reject-occupancy.npz)与[体素分析](../../artifacts/runs/p2-ego-full-spline-guard-delayed-goal-20261021-330/guard-snapshot-analysis-01.json)。
- 未验证与 PROVISIONAL：较长预建图和运动没有消除当前位姿起点cell unknown。地图是内部在线估计、无独立真值；unknown不等于物理free。邻近 free cell 不证明未观测 cell 或机体周边安全。没有 spline，因此无全曲线净空；无机体扫掠、控制执行、跟踪/制动、PX4或实机证据。GOAL C继续pending。
- 下一步：审查深度投影/free-ray更新与机体位姿周围unknown体素的成因，核对坐标与D435i视场/机体占据关系；保持unknown阻塞，只有合同和几何证据能支撑的表示方式才进入隔离候选。

未提交；保留工作树中已有用户修改，本轮无暂存或提交。
