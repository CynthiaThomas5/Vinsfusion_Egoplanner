# GOAL C B-spline 同 stamp 占据快照 #316

对话摘要：[2026-10-20-065](../../collaboration/dialogues/2026-10-20-065-p2-ego-spline-snapshot-clearance.md)

本轮没有改 planner 源码。复用 #315 的同一隔离二进制，在 planner-only probe 收到每个不同 B-spline 后异步请求 canonical EGO patch 0021 提供的只读 `/mapping/get_occupancy_snapshot` 服务；分别保存 occupancy/inflation NPZ 并离线采样曲线。新增素材、脚本、快照和原始日志归档在 `artifacts/runs/p2-ego-global-plan-snapshot-clearance-20261020-316/`。

运行中定位、MapStatus ready 并发出目标 `[2.5,1.4]`；探针收到3个不同 trajectory ID，并收到3个 exact epoch/map_id匹配的服务响应。Map大小240×240×60、resolution 0.1 m，known voxel占全图0.591–0.615%；源龄99–110 ms。服务response stamp相对 spline `start_time` 为 +1 ms、0 ms、0 ms。重建B-spline后每10 ms采样并依照 `posToIndex=floor((p-origin)/resolution)` 查raw occupancy与inflation mask：474/464/896个样点全部在图内且均为known-free，无raw occupied样点；轨迹ID2/3另有10/6个样点落入inflation mask。三条曲线到occupied voxel axis-aligned cell box的最小离散样本距离为0.659/0.637/0.512 m。既有名义球半径0.482 m下，第三条余量约30 mm。

隔离源码审计发现该EGO版本以`inf_step=ceil(0.5/0.1)=5`并填充`[-5,5]³`扩张膨胀mask，因此mask命中可发生在大于0.5 m球面距离的对角区域。该解释不能证明轨迹安全；已知地图覆盖不到0.62%，每个点查询不等于扫掠机体包络，未运行轨迹服务器、controller、PX4或真值订阅，三条轨迹均未执行。

验证：`bash artifacts/runs/p2-ego-global-plan-snapshot-clearance-20261020-316/run-container.sh`（目标探针收到3条 spline，snapshot service调用3次，无truth/control节点和topic）；`python3 -m py_compile` run-local probe/analyzer；`bash -n` runtime scripts；offline `analyze_spline_snapshot.py` 与其JSON读回通过。构建复用#315五包Release build和4/4端点测试，未重建 planner。

证据：[报告](../../progress/evidence/p2-ego-spline-snapshot-clearance-20261020-316.json)、[曲线分析](../../artifacts/runs/p2-ego-global-plan-snapshot-clearance-20261020-316/spline-snapshot-clearance-analysis.json)、[运行manifest](../../artifacts/runs/p2-ego-global-plan-snapshot-clearance-20261020-316/runtime-manifest-01.json)。下一步审查 optimizer 对轨迹曲线的碰撞采样规则与 cube inflation mask 的关系，再重复独立epoch和第二障碍布局；GOAL C/D/F保持pending。
