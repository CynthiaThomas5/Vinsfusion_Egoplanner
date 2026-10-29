# #120 N06.4 全机支架释放准入复核

日期：2026-10-23。对话摘要：[2026-10-23-120-n06-support-release-admission.md](../../collaboration/dialogues/2026-10-23-120-n06-support-release-admission.md)。证据报告：[n06-support-release-admission-20261023-120.md](../evidence/n06-support-release-admission-20261023-120.md)。

## 目标与范围

Goal 完成模式，父目标 N06，子项 N06.4。使用 DISARMED PX4 SITL 状态完成全机支架扫描、detach 和释放后 fresh N05 online/offline admission。PX4 不武装，bridge 保持 DISABLED；不发布 ROS 控制／导航目标，不执行规划曲线，不订阅真值用于准入，不连接实机。

## 实际改动

- 将 D435i include 位姿显式设为 `relative_to="base_link"`；几何导出、N05 包络、包络审计和测试校验 include 与 fixed joint 的参考帧及变换一致，并更新包络源 hash。
- 为低位地面可见性增加 profile `n06_full_airframe_retreat_240_oblique_early_view`；在 x=−1.2 m 静止俯视后，保持视角完成−2.4 m 后退。集中 profile CLI choices，并新增选择回归断言。
- 不修改 N05 unknown 策略、几何门限或 GOAL 完成契约。
- 补建 #120 对话、证据与改动记录；CURRENT、milestones、执行书只登记结果并保留 N06 `in_progress`。

## 验证与结果

构建、SDF、几何／包络／profile 定向测试、runner 语法、JSON、结构检查及运行前 `git diff --check` 结果见[证据报告](../evidence/n06-support-release-admission-20261023-120.md)。

运行 `n06-20261023-wall-145` 完成 12/12 阶段，x 轴实测后退−2.400407 m；15,226 条扫描 trace 的定位状态均为 valid/tracking，同一 epoch 和 map_id 保持。post-release raw ground plane 有效（z=−0.350 m，126 个 raw occupied voxel），但 fresh N05 online/offline 均因 TAKEOFF_CONTACT unknown 拒绝。后释放后 TAKEOFF 最大 unknown 从 #142 的 483、#145 before 的 480 降至 38；HOLD 为 0，但起飞／着陆接触体积仍无法通过。

离线复算定位到 38 个 TAKEOFF unknown voxel centers 全在拟合地面以下。它们属于不透明地面下方、相机无法观测的体素；继续变换观察方向不能将其变为 raw free。夹具 helper 在 detach/removal 后的健康等待抛出通用 localization 错误，原始失败保留；扫描 trace 行均有效，runner 仍完成了独立 post-release admission。所有 PX4 状态样本均 DISARMED，bridge DISABLED，夹具确认 detach/移除，项目容器无遗留。

`n05-run-summary.diagnostic_pass=true` 仅代表诊断流程记录及安全检查完成；`post_release.transfer_gate_passed=false` 是入口未通过的最终事实。完整运行产物、报告哈希和局限见[证据](../evidence/n06-support-release-admission-20261023-120.md)与 `artifacts/runs/n06-20261023-wall-145/`。

## 未解项与下一步

N06 仍需现行规则下的全机释放后正向 N05 admission；只有入口转为正向，才进行受影响 N05 和当前补丁版 N06 planner 的双布局复核。现有 planner-only 两布局证书不能替代入口。N06 原有通过门限和父状态未改；N07 未启动。

报告提出一个待用户决定的最小语义澄清：在 fresh raw-ground plane 与 PX4 landed 已确认时，只豁免整个 voxel cell 完全位于地面以下的体素；与地面相交／高于地面、地面支撑区外、过期或越界 unknown 仍拒绝。该建议涉及当前 fail-closed unknown 条款，本轮未实现。停止原因是再做相机视角扫描无法提供新判别信息；等待规则决定或新的合规观测几何证据。
