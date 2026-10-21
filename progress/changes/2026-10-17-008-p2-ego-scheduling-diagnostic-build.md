# P2 EGO 调度诊断构建与首次运行

日期：2026-10-17。对话摘要：[2026-10-17-008-p2-ego-scheduling-probe-startup.md](../../collaboration/dialogues/2026-10-17-008-p2-ego-scheduling-probe-startup.md)。

- 修改：新增 EGO patch 0012，增加 steady-clock 的同步输入 callback age／duration、occupancy timer start-to-start gap 与最近 occupancy fusion duration，只增强日志，不改变映射行为。patch SHA256 `2c9ea857cbbb1cd3bd4b2b8a678a3bf59e60bfac4bf9f8db7d24eab0c800b833`；当前 vendor 源树未编辑。
- 验证：patch 以当前 post-0011 源 hash 为基准并可 byte-exact replay。隔离源码副本 Jazzy overlay 5/5 包构建通过（`plan_env`、`traj_utils`、`bspline_opt`、`path_searching`、`ego_planner`），colcon exit 0、134.93 s；事件日志和安装文件哈希见[构建报告](../evidence/p0-ego-map-timeout-diagnostic-build.json)。
- 运行：run #25 的深度健康状态为 READY，但定位适配器在12.183墙钟秒进入 `initialization_timeout`，没有优化里程计、EGO depth/pose 配对或占据点。该运行排除，不作为 EGO timeout 或地图时序证据；诊断 overlay 确已由运行脚本 source，但诊断回调未被触发。原始报告和日志及哈希见[输入间隔报告](../evidence/p2-ego-input-interval-diagnostic.json)。
- 后续运行结果：run #29 使用正确 epoch 并读取 patch 0012 指标，steady-clock 显示 callback约1 ms、timer间隔约50 ms、融合约3–4 ms。run #32/#33 的 patch 0013 计数将停顿定位到 EGO pose 接收路径；patch 0014 history 100 未消除。当前根因与阈值仍未解决，见 [011](2026-10-17-011-p2-ego-pose-receipt-diagnostic.md)。

- 后续排查修正：run #25–#28 的复测脚本在复制时没有更新 `VINS_NS` 取值路径，实际读取 run #24 manifest，使 VINS 输出到旧 epoch namespace。此前将 `initialization_timeout` 解释为定位启动不稳定的判断撤回；详情见[namespace 修正记录](2026-10-17-010-p2-vins-session-namespace-fix.md)。
