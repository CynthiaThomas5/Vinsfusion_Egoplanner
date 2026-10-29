# N08.2v #232：负 Y 覆盖尝试在支架 yaw 段中止

## 结果

N05 支架扫描只完成 9/19 stages，随后定位状态转为 `normalized_cost_exceeded`（cost 1.702）。没有进入 post-release/current-area admission，也没有启动 compute-only；本次没有新鲜地图或负 Y hold 覆盖结论。车辆已 landed，fixture 已 detach 并从 Gazebo 移除，容器停止并 exit 0。无 XY、无制动测量。

## 失败发生在哪一段

- Run：`n08-20261024-232-negative-y-hold-compute-01`，profile `n08_overhead_rear_one_side_view`，场景 `n08_overhead_calibration`。
- scan 前 online/offline N05 admission 均一致拒绝 `ground_plane_insufficient_raw_occupied_voxels`；这是支架扫描前地图，不是 scan 后 gate。
- 实际 profile 在 indexes 9–10 先转到 yaw `+π/2`、pitch `−0.45`；indexes 12–13 才转 yaw `−π/2`、pitch 0。helper 在 stage 9 执行期间失败，negative-y 水平视角**没有到达**。所以 #232 没有测试原先预期的负 Y 观测效果。
- trace 截止时最新样本仍为 valid、cost 0.527、yaw 0.708 rad、pitch −0.203 rad；trace 中最大 cost 0.653。之后 helper 读到 state 4 / `normalized_cost_exceeded` / 1.702。触发时刻没有被 trace 采到，故不能断言 yaw、pitch 或场景中的哪一个因素是根因。
- 9 个已完成 stages、attached→detached、fixture model absent、最终 landed 均有记录。N05 probe exit 1；外层 runner exit 12。随后 `bash tools/project.sh stop n08-20261024-232-negative-y-hold-compute-01` exit 0，container `Exited (0)`，无本 run 进程。

## 影响和下一项

此结果不推翻 #231 same-run 地图上负 Y unknown 的诊断，但也不验证补图假设。当前 `n08_overhead_rear_one_side_view` 实际包含两个侧向段；它不是仅负 Y 的 profile。下一步建立一个只含负 Y 水平观察的独立 profile，保留已完成的 overhead/地面扫描阶段和其余门限，移除先行的 `+π/2, −0.45` 观察，再以 fresh N05 gate 验证。若扫描健康门再次拒绝，就停止该路径并记录为安全阻塞，不运行 compute-only。

完整原始记录位于 `artifacts/runs/n08-20261024-232-negative-y-hold-compute-01/`，重点为 `fixture-result.json`、`fixture-stages.json`、`fixture-trace.jsonl`、`n05-prescan-ready.json` 和 `n05-fixture.exitcode`。机器可读摘要与 SHA-256 见同名 JSON 文件。
