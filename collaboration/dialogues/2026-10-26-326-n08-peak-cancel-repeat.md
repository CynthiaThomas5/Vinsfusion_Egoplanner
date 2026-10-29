# N08 #326：计划中的近峰值速度取消补测

用户授权在现有规划内完成 N08。三次普通 `single_goal terminal_stop` 已由 #322、#324、#325 累计通过；这次补测来自 [N08 测试计划 D.6](../../docs/n08-completion-test-plan.md)：在低速取消链通过并完成预算初版后，另在实际前向峰值约 0.08 m/s 处取消一次。

现有 #321 最大实际速度为 0.08585 m/s，但取消请求发出时 PX4 水平速度只有 0.04014 m/s、EGO 参考速度 0.05848 m/s，因此不能把它当作 0.08 m/s 取消触发证据。#326 使用 0.08–0.09 m/s 的 PX4 水平速度触发窗口，重用 runtime-contract `75aaa541f7684b38fe0805b958e029fa21f8c6dd6ab00d2ebe1fae92c7e8a772`、同一目标／planner 配置和既有 raw-map／动力学／健康限制；不修改代码、配置或正式阈值。

通过判据：同一性新鲜的 N05／全机前向 corridor admission、native caller-cancel action 终态正确、EGO 替换停止样条通过动力学和地图证书、旧轨迹不恢复、取消至停车在 0.50 m 候选范围内、停车保持及终点落地通过、PX4 disarmed/landed、独立 evaluator PASS。若前置准入拒绝或触发窗口未出现，保留拒绝／失败证据，不把它计作取消测量；结束后再进行 N08 最终预算审计。

## 执行结果

#326 的 N05 支架路线完成六阶段，但释放后的 fresh N05 接触体积仍有 51 个 raw-unknown cell，online/offline 同身份一致拒绝。40.001 秒只读 preflight 通过，拒绝不是时钟／里程计新鲜度锁存。没有 goal、enable 或飞行；6 秒独立读回为 DISABLED/disarmed/landed 且控制采样为零，随后 container exit 0。未知体素只读坐标审计见 [#326 refusal report](../../progress/evidence/n08-cancel-peak-refusal-20261026-326.md)。因此此近峰值触发窗口没有通过，也不计取消测量。

随后完成 N08 正式出口最终审计：#322/#324/#325 在同一冻结版本下普通单目标累计 3/3；#321 的独立低速 caller-cancel 停止／保持链通过。官方 N08 出口无需额外三次取消，也未把建议的近峰值取消窗口升级为门槛；#326 按 safe fail-closed 记录为详细计划的未取得数据项。无阈值、代码或配置变更。
