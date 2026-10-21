# GOAL C EGO pose reader 回执与同戳样条快照诊断 #345

## 结果

从#341 run-local EGO源码副本重建隔离 overlay，并在0033之后应用新诊断补丁0034。补丁通过零fuzz replay；Jazzy Release五包构建（`plan_env`、`traj_utils`、`path_searching`、`bspline_opt`、`ego_planner`）通过。0034只在现有 `message_filters` 深度与位姿reader记录回执计数、末条源戳及RMW message-lost事件，不改变QoS、同步策略、地图融合、规划守卫或0.4秒freshness门。

在新ROS domain #345 中，EGO记录27条timeout警告，仿真时间18.658–19.552 s。期间深度reader计数390→417、源戳18.547→19.438 s；位姿reader与同步对计数固定379，末条位姿戳18.184 s；两路RMW message-lost均为0。该时间窗早于pitch及goal，未在同窗采集adapter侧camera-pose发布，因此证据将停滞定位到EGO位姿reader回执边界，尚不能区分发送端、DDS或executor调度原因。本轮没有 `Depth Lost! EMERGENCY_STOP` 记录。

之后发送匹配epoch的 `/navigation/ego_goal` `NavigationCommand`，目标为`[0.25,-0.15,0.4]`。同epoch/map_id前后pitch快照将目标体素`[122,118,5]`从unknown改为free且未膨胀。EGO输出一条目标B-spline并取得同epoch/map_id/frame只读snapshot；snapshot戳与`spline_start_time`完全相同，深度源龄104 ms。独立de Boor按完整活动区间每10 ms采样103点：42点在当前起点unknown voxel `[120,119,1]`，61点known-free，0个occupied、inflated或越界点。最接近起点的里程计样本早5 ms；endpoint距请求目标约1.02 cm。

起点unknown样点仍依赖实验补丁0033的窄例外，其他unknown仍被阻塞。曲线未执行；中心线不代表机体swept volume。没有controller、trajectory server、PX4、真值输入或控制话题，GOAL C继续pending。

## 验证

- `patch --dry-run --fuzz=0 -p1` 和应用0034：通过；仅写入#345源码副本。
- `bash artifacts/runs/p2-ego-observed-voxel-reader-receipt-diagnostic-20261021-345/build-ego.sh`：五个EGO包Release构建通过。
- `bash artifacts/runs/p2-ego-observed-voxel-reader-receipt-diagnostic-20261021-345/run-container.sh`：planner-only复测退出码0；图中无truth/control话题或controller/PX4节点。
- `python3 -m py_compile .../analyze_spline_snapshot.py` 与独立样条/occupancy分析：8/8身份、范围和隔离检查通过；完整活动区间103点分类为42 unknown、61 free。
- run manifest与轻量evidence哈希及结构状态将在最终检查中复核；GOAL C保持pending。

证据：[轻量报告](../evidence/p2-ego-observed-voxel-reader-receipt-diagnostic-20261021-345.json)、[run manifest](../../artifacts/runs/p2-ego-observed-voxel-target-reader-receipt-diagnostic-20261021-345/run-manifest.json)、[样条分析](../../artifacts/runs/p2-ego-observed-voxel-target-reader-receipt-diagnostic-20261021-345/spline-snapshot-analysis.json)。补丁基准、哈希和run-local应用顺序见[依赖说明](../../dependencies/README.md)。对话摘要：[2026-10-21-012](../../collaboration/dialogues/2026-10-21-012-p2-ego-observed-voxel-reader-receipt-diagnostic.md)。

## 下一步

在同一短时窗并列采集adapter侧depth/camera-pose输出戳与EGO实际reader回执，确认暂态差异出现在发送端还是订阅/调度边界；不改变QoS、未知空间策略或0.4秒门。输入稳定后再做第二布局和机体包络unknown量化。完整swept-volume与安全pitch合同通过前不执行PX4动作。
