# #495 N12 证据与任务profile修复

关联对话：[复核决定](../../collaboration/dialogues/2026-10-29-495-n12-first-flight-review.md)。

#494首次分析缺主仓库legacy目标文件路径，补同字节原文件后新目录复算，旧不足报告保留。离线绕行判断器修正重复源戳：同戳truth/同轨迹参考必须逐字一致；不同轨迹交接须已有匹配goal/epoch样条，零时间不作插值和时间信用；仍拒绝倒退和矛盾。13项几何/重复/交接验证通过，#494绕行重放PASS但原两项真实失败不变。

profile v2仅请求驻留4→5sim秒，依据#494独立到达2.956s及后续1s诊断3.956s；独立3s门限和全部数值标准保留。修复prepare helper同时归档实际flight记录引用的legacy目标路径。新外部release冻结runtime/配置/协议/评估器身份；未改候选运行源码或二进制。下一#496正式02。报告详见progress/evidence/n12-evidence-review-20261029-495.md；最终结构/diff检查在本轮收尾执行。
