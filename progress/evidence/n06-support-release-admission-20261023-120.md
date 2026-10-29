# N06.4 全机支架释放后准入诊断（#120）

日期：2026-10-23。目标：Goal 完成模式下推进 N06.4，验证修正相机安装帧后的全机支架扫描能否在释放后通过 fresh N05 准入。运行仅使用 DISARMED PX4 SITL 状态，bridge 保持 DISABLED；不发布 ROS 控制或导航目标，不执行规划曲线，不使用在线真值，不连接实机。

## 结论

**N06 仍为 `in_progress`，本轮没有建立合法正向入口。** 当前补丁版 planner 子项的已有证据继续有效；缺口是完整 X500 支架扫描、支架释放后重新采集的 N05 在线准入尚未返回 `accepted=true`。

运行 `n06-20261023-wall-145` 完成了 12/12 个扫描阶段，实际后退约 2.4004 m 并返回。15,226 条夹具 trace 均记录 VINS `valid=true`、tracking 状态 1、同一 epoch；运行前后 `epoch` 与 `map_id` 一致。修正早期俯视后，低位包络 unknown 大幅减少，但释放后 TAKEOFF_CONTACT 仍有 38 个 unknown cells，在线和离线均以 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` 拒绝。

离线复算发现，释放后 TAKEOFF_CONTACT 相交的 38 个独立 unknown voxel centers 全在拟合地面下方：36 个中心 z=−0.455 m、2 个中心 z=−0.555 m；raw occupied 地面平面 z=−0.350 m，分辨率 0.1 m。这些格子的整个垂直范围均低于地面表面，最低仅比地面低 0.055 m。增加相机视角不能把不透明地面下的体素观测成 free；继续扫视角不会满足当前“扩展包络中的 unknown 拒绝”规则。该结论来自当前模型、地图和包络的证据；它不构成修改 unknown 规则或宣布通过的授权。

## 本轮改动与既有验证

修正了 `simulation/models/x500_d435i/model.sdf` 中 D435i include 的坐标参考：显式相对 `base_link` 放置，使 Gazebo 装配高度与固定关节声明一致。几何生成、N05 碰撞包络、包络审计和回归断言现均检查 camera include 与 fixed joint 使用相同参考帧和位姿。更新了 envelope 的模型源 hash。

新增全机支架扫描 profile `n06_full_airframe_retreat_240_oblique_early_view`：在 x=−1.2 m 先静止俯视 +0.45 rad，再保持视角退至 −2.4 m。profile CLI 选择项集中到 `PROFILE_CHOICES` 并加入回归断言。

改动后的定向验证记录：

- `python3 tools/test_sim_geometry.py`：5 passed。
- `python3 tools/test_vehicle_envelope.py`：3 passed。
- `python3 tools/test_preflight_scan.py`：19 passed。
- `python3 tools/audit_vehicle_envelope.py`：通过。
- `gz sdf -k simulation/models/x500_d435i/model.sdf`：Valid；展开后的动态 pose 中 base_link 相对 X500 根 z=+0.24 m、camera link z=+0.32 m，二者相对高度 +0.08 m，与 joint 一致。
- `colcon build --base-paths src --packages-select uav_sim --parallel-workers 1 --cmake-args -DCMAKE_BUILD_TYPE=Release`：1 个 package 构建完成。
- `bash -n tools/run_n05_preflight_layout.sh`、`python3 -m json.tool config/components/simulation/preflight_scan.json`：通过。
- `python3 tools/project_status.py`：结构检查 PASS；报告 80 个缺失的历史可选 artifact links。该检查不是 SITL 或运行验收。
- `git diff --check`：通过。

## #145 实际运行

| 项目 | 结果 |
| --- | --- |
| Profile / layout | `n06_full_airframe_retreat_240_oblique_early_view` / `wall_box_column` |
| spawn | x=−6.5 m；运行时配置由 trap 恢复，当前 `config/runtime.json` SHA-256 为 `a862e521dd738dba71d960cda95458509336f1e2cd845228b46311fd57928221` |
| 扫描 | 12/12 stages；主要 x 关节最低 −2.400407 m；trace 15,226 行，sim 16.348–377.392 s |
| 定位和地图身份 | trace 每行均 valid/tracking、单一 epoch `d0cee37249c1472d80e3490a47892359`；before/after map_id 均为 `d0cee37249c1472d80e3490a47892359-24ad64b9f32d434e8f162cbb4c8047c5` |
| 地面 | raw occupied plane 有效，z=−0.350 m，126 个 raw occupied voxels，xy span 1.4 × 1.9 m |
| after gate | online/offline 一致拒绝；TAKEOFF unknown 36，ASCENT/DESCENT 各有 18/19 样本通过、最大 unknown 32，HOLD 1/1 通过且 unknown 0 |
| post-release gate | 在线/离线一致拒绝；TAKEOFF unknown 38，ASCENT/DESCENT 各有 17/19 样本通过、最大 unknown 32，HOLD 1/1 通过且 unknown 0；`transfer_gate_passed=false` |
| 安全状态 | 730 个 PX4 状态样本均 DISARMED；bridge DISABLED；无控制／目标发布；真值未用于准入；fixture 已 detach、移除服务确认且 Gazebo model list 中不存在 |

`n05-run-summary.json` 的 `diagnostic_pass=true` 只表示记录、identity、安全移除和在线／离线诊断检查完整，不能解释为准入通过。fixture helper 最后在 detach/removal 后的健康等待期间抛出 `localization changed or became invalid during physical scan`；已保存的 15,226 条扫描 trace 全部有效，释放后在线报告也记录 localization 有效。此 helper 错误保留在原始结果中，不把它抹去或改写为全流程 PASS。runner 仍完成独立 post-release fresh admission。

## 仍缺的出口与决策边界

N06 还差：

1. 按现行规则取得全机释放后的 fresh N05 `accepted=true` 正向入口；本轮只有 wall 布局拒绝结果。
2. 只有入口为正向后，按原计划在两个布局复核受影响的 N05 与当前补丁版 N06 planner 出口，并完成父目标审计。当前 N06.2 的双布局 planner-only 子项并不能替代这项准入。

当前准入配置明确将扩展包络中的 unknown 视为拒绝项。可供用户决定的最小语义调整建议是：在有效 fresh raw-ground plane 和 PX4 landed 状态确认后，仅把**整个 voxel cell 都位于拟合地面以下**的格子视为地面遮挡体积；与地面相交、地面以上、地面支撑区域外及地图外的 unknown 继续 fail-closed。此规则会改变现行 unknown 接受边界，因此本轮没有实现、没有重放假设结果、没有改阈值或里程碑状态。未得到决定前，N06 保持未通过，N07 不启动。

## 归档与哈希

运行目录：`artifacts/runs/n06-20261023-wall-145/`。

关键 SHA-256：

- `n05-run-inputs.json`：`51f6e6ac5e90b1325a2e844a2ba5e112df93d52c98e8bbcb790a097580ef2164`
- `fixture-result.json`：`c90f71ee5c5ae68c811220429e550d047a5cebad8658d3253661ed038fb81361`
- `fixture-trace.jsonl`：`cdbb7c42ec38854b00baabdc0e88b6fc5f92768100ddd2fb0e5174786aa64305`
- `n05-run-summary.json`：`e8dedd5fe3dfc57b6e7176edebb55bb114fb17f418a660e0ff085d7abbf0a462`
- `n05-post-release/n05-live-entry-check.json`：`aad11e38b637cabe3faa1178e1a73b9d37ce6a1f1435bddfa54c293dd0377cda`
- `n05-post-release/n05-offline-entry-replay.json`：`d9f92d3f1eaf5e8b9e1ccbca2c01a7ce3915312ce052b67a659b2d8155db21d8`
- `n05-post-release/n05-live-raw-map.npz`：`16584e77c15ef01a43218652b77f0e988f95c7f955118fbaf4583e3da7f394ce`

停止原因：现行 unknown 规则下，#145 的 remaining rejects 已定位到地面以下不可由 D435i 观测的 voxel cells；继续更换观察角度没有判别价值。下一步取决于是否批准上述规则语义调整，或维持原标准并将当前入口判为未通过。
