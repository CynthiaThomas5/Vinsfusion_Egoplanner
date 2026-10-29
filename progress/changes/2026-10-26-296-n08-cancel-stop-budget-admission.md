# 2026-10-26 #296 N08 制动预算与准入接线

- 增加唯一配置项 `cancel_stop_distance_envelope_m=0.50`，并说明其仅适用本次有限样本低速前向取消协议。
- N08 前置和空中原始地图走廊准入现在实际消费该值；runner 在请求取消前检查剩余前向走廊；offline evaluator 同一 run 参数化检查。没有放大机体半径、N05 uncertainty、0.25m tracking margin 或0.15m tracking门槛。
- #212/#257/#260 的模式和 runtime-contract 对照、#260/#267/#273 正常制动与 #292/#294 取消数据汇总到 [#296 evidence](../evidence/n08-cancel-stop-budget-admission-20261026-296.md)。
- 验证：`bash tools/project.sh test`：361 项单测和 navigation-adapter integration 通过。
- 局限：#292 只作部分取消测量；#294 为完整低窗口取消通过；较高速度窗口与最终 3 次同版本普通单目标仍待执行。
- 对话摘要：[2026-10-26-296](../../collaboration/dialogues/2026-10-26-296-n08-cancel-stop-budget-admission.md)。
