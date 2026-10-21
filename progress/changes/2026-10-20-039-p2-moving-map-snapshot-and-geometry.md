# 修改与验证记录

- 任务 ID／日期：P2 动态地图快照、几何探索与时钟诊断闭环 #274–#279／2026-10-20
- 对话摘要：[039 对话摘要](../../collaboration/dialogues/2026-10-20-039-p2-moving-map-snapshot-and-geometry.md)
- 修改文件：`src/own/uav_localization/uav_localization/health.py`、`src/own/uav_localization/uav_localization/node.py`、`tools/test_localization_health.py`；新增#278运行报告并更新#279运行报告；新增[合并证据](../evidence/p2-moving-map-snapshot-20261020-278-279.json)；更新#247/#273的EGO接线资格说明、`README.md`、`progress/CURRENT.md`、证据索引、GOAL checklist 与里程碑。
- 行为变化及原因：future-stamp guard触发时保留精确消息源stamp、adapter clock、年龄和容差，并在该epoch发出一次诊断行；健康阈值和锁定行为不变。对旧run核对EGO输入后，将`odom`与定位适配器实际输出的topic mismatch从规划健康证据中剔除。
- 验证命令与结果：`python3 tools/test_localization_health.py`（12 tests passed）；定位健康代码和测试`py_compile`通过；固定镜像下#277、#278、#279新overlay分别4/4包构建通过；#279重新运行`tools/export_occupancy_snapshot.py`，metadata内run-report SHA与最终报告一致，1191点PCD float32逐点回读一致。
- 运行证据：#278在probe开始0.823 s以`telemetry_stale`锁定，虽观察3条ready MapStatus，但状态／cloud未精确配对，排除归档验收。#279在35.023 s观察窗中MapStatus 153/153 ready、定位692/692 valid TRACKING、深度健康1317/1317 ready；运动记录区间内264个地图样本有122次点数变化。运动记录结束后捕获1191点同epoch快照。单SE(3)、固定尺度离线轨迹对齐379对位置RMSE 8.16 mm；箱体／圆柱ROI各45/31点，表面残差P95 5.56/11.00 cm。EGO正确订阅`/localization/optimized_imu_odom`并到达WAIT_TARGET，但记录51条`odom or depth lost!`、未发goal，根因未定。
- 未验证与局限：#279 snapshot stamp 34.061 s晚于motion driver记录结束32.342 s；运动区间点数变化只证明地图输出在更新，不证明覆盖或几何正确。PCD仅occupied；free/unknown、持久覆盖、地图净空、碰撞、规划轨迹与PX4均未验收。几何ROI稀疏，正式GOAL F阈值未冻结。健康阈值未变，GOAL C/F与整体A–H仍pending。
- 下一步：先在正确里程计接线下追踪EGO pose与occupancy reader边界，解释51条输入超时；随后定义覆盖/free-unknown/clear-path验收标准并补相应无真值测试。

本轮未提交或推送。
