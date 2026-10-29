# N08 正式出口完成审计

用户要求按既定规划完成 N08，并确认普通目标到达即结束，不隐含返航；返航属于后续独立命令。目标范围为当前单 D435i 仿真，不重测已通过的 N07，不降低门槛。

本轮完成同冻结版本下 #322/#324/#325 三次普通单程 `terminal_stop` 累计通过。复用 #212 hold 基线、#257/#260 同 runtime-contract 的 compute-only/native-execute 对照，及 #321 独立 caller-cancel 停止／保持通过链。N05/N06 预算来源和实际 gate 消费审计完成。

为完整核对详细计划 D.6 的建议补充，在 0.08–0.09 m/s 触发窗口启动 #326。扫描和支架释放后 N05 fresh 接触包络仍有 51 个 raw-unknown cells，在线与离线对同身份一致拒绝；preflight 通过，但没有 goal、enable 或 flight。6 秒 PX4/bridge readback 确认 DISABLED/disarmed/landed/control0，仿真以 exit 0 停止。保持拒绝结果，不调阈值。该额外速度窗口无测量，作为计划扩展未完成项记录；它不是 N08 正式出口要求的额外取消重复次数。

最终 audit 将 N08 状态设为 `passed`，execution_plan 指针设为 N09；N09 尚未开始。当前没有待用户决策项。
