# GOAL C 密集曲线校验后的同刻快照 #319

对话摘要：[2026-10-20-068](../../collaboration/dialogues/2026-10-20-068-p2-ego-dense-spline-snapshot-validation.md)

使用 #318 构建的 patch 0029 planner binary，不重建源码。新的 D435i/VINS epoch 中探针收到2个 spline ID；ID 1的snapshot请求被`no_fresh_fused_depth`拒绝，ID 2成功。其快照 stamp 与 spline `start_time` 完全一致，深度源龄66 ms。重建曲线每10 ms取样414点，全部在地图内、known-free，raw occupied和inflation mask均为0；到occupied voxel box最小距离0.6277 m，名义球半径0.482 m余量0.1457 m。

验证：`bash artifacts/runs/p2-ego-dense-spline-snapshot-validation-20261020-319/run-container.sh`；`python3 artifacts/runs/p2-ego-dense-spline-snapshot-validation-20261020-319/analyze_spline_snapshot.py`；两份 shell runner `bash -n`，probe与分析脚本`py_compile`。#318已对相同binary完成五包Release构建和4/4端点用例。探针图无truth/control topic、PX4/controller/traj_server；轨迹未执行。

证据：[报告](../../progress/evidence/p2-ego-dense-spline-snapshot-validation-20261020-319.json)、[runtime manifest](../../artifacts/runs/p2-ego-dense-spline-snapshot-validation-20261020-319/runtime-manifest-01.json)、[离线曲线分析](../../artifacts/runs/p2-ego-dense-spline-snapshot-validation-20261020-319/spline-snapshot-clearance-analysis.json)。known覆盖仅约0.62%，中心线未扫掠机体包络，也无地图准确度、跟踪误差或真值证据；这是一次实验性中心线对照，不是安全通过或canonical验收。P2健康阈值与GOAL C/D/F状态不变。
