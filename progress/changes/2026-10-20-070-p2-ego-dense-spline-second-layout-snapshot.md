# GOAL C 第二障碍布局同刻快照复测 #321

对话摘要：[2026-10-20-070](../../collaboration/dialogues/2026-10-20-070-p2-ego-dense-spline-second-layout-snapshot.md)

针对#320的两次`depth_pose_gate_closed`，新epoch复跑相同第二障碍布局并使用具有瞬时服务门控重试能力的observer。两次服务请求均在首次调用接受；对应spline start_time与快照stamp相差+1 ms、0 ms，source age 130 ms、99 ms。offline分析中两条完整active中心线在10 ms样点上均为known-free，0个unknown、raw occupied或inflated命中；离散中心线到occupied voxel box最小距离0.542/0.592 m，既有名义球半径为0.482 m。

验证：`bash artifacts/runs/p2-ego-dense-spline-layout-snapshot-retry-20261020-321/run-container.sh`；`python3 artifacts/runs/p2-ego-dense-spline-layout-snapshot-retry-20261020-321/analyze_spline_snapshot.py`；runtime shell runners `bash -n`，probe/analyzer `py_compile`。planner binary复用#318已构建五包Release overlay及4/4端点用例。无controller、trajectory server、PX4、truth/control topic，轨迹未执行。详见[证据](../../progress/evidence/p2-ego-dense-spline-second-layout-snapshot-20261020-321.json)、[runtime manifest](../../artifacts/runs/p2-ego-dense-spline-layout-snapshot-retry-20261020-321/runtime-manifest-01.json)和[曲线分析](../../artifacts/runs/p2-ego-dense-spline-layout-snapshot-retry-20261020-321/spline-snapshot-clearance-analysis.json)。known覆盖约0.58–0.59%，无机体扫掠、地图准确度、跟踪误差或真值；只作为第二布局中心线诊断，goal/milestone状态不变。
