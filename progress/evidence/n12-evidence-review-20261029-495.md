# #495 N12 证据复核和profile v2

#494的失败保留。2546个同源戳记录无时间倒退；同戳truth完全相同，38个参考变化全部对应不同轨迹ID。只读判断器现接受逐字相同回执，以及已由goal/epoch样条ID验证的交接；不为零时间交接贡献插值或驻留，真时间倒退/同ID矛盾仍拒绝。13项定向验证通过。#494原始数据重算绕行证明PASS，完整合同仍FAIL。

到达不足实际由yaw较晚进入15°容差造成。原native4秒到达的真实联合驻留仅2.956秒；额外观察后续1sim秒（只作诊断）形成3.956秒。下一profile仅把请求驻留4→5sim秒，真实验收仍位置≤0.3m、yaw≤15°、连续≥3sim秒；20sim秒post-goal hold不计到达。此修改不是RPE修复。

RPE异常窗起点集中前20秒，分段P95约0.05434/0.05339m；后续起点20–50秒P95约0.04643/0.03894/0.02858m。各段特征充足、solver usable=100%、waiting features和pending span均0；尚无证据定位内部估计偏差根因，原0.05m标准保留。#496在native dwell5这一唯一任务请求变量下检验实际到达，RPE继续独立验收；若再次超限，先用固定输入定位实现机制，不盲目增加同类飞行。

运行runtime仍90fd8dae...，唯场景相对N11改变；profile/evaluator修订在独立release重新冻结，当前无成功次数损失。原#493清单/协议和#494全部原报告保留。[新冻结清单](../../artifacts/runs/n12-20261029-495-review/release/freeze-inventory.json)、[RPE分段](../../artifacts/runs/n12-20261029-495-review/494-review.json)、[到达与telemetry分析](../../artifacts/runs/n12-20261029-495-review/494-arrival-telemetry-review.json)。下一项#496正式02。
