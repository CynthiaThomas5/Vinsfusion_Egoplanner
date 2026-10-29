#268 对话摘要

- 延续用户明确的返航规则：不倒飞；在已认证 hold volume 内由 EGO 原地转头约 180°，确认航向后等待新融合图，再由 EGO 机头前向返航。
- #267 的 0.6 m 制动测量成功，但转向 hold 球内 30 个后向 raw unknown 阻止转向。起飞前同一空间曾是 free，飞行后 fresh map 中转为 unknown。
- 新假设：在原测量段结束后，若 turn-hold 仍因 unknown 被拒，只做一次 fresh-map 认证的 0.22 m 前向 EGO 定位目标，再用新 fresh map 重查真实转向球。0.22 m 高于 EGO 的 0.2 m 最短局部路径要求。
- 实现保持 0.25 m tracking margin、5 cm 横／垂曲线管道、0.12 m/s vector cap、raw unknown fail-closed 和先转头后返航的顺序。制动评估窗口仍结束于原 0.6 m goal 的 stop/hold。
- 门控测试 9/9、脚本语法、diff 检查通过；新的全新 SITL 仍待执行。N08 保持 `in_progress`。
- #268全新SITL完成N05扫描15/15、post-release与mission current-area准入及40.005秒preflight；首条0.6m曲线被原5cm连续管道拒绝，实测最大偏差5.265cm（超2.647mm）。新增的0.22m前移、转头和前向返航没有执行，安全落地停止。证据：[报告](../../progress/evidence/n08-forward-positioning-return-refusal-20261025-268.md)。
- 下一子项#269：保留总速度<0.03m/s稳定1秒，增加垂向速度<0.01m/s稳定1秒后才允许发首条目标；该条件是诊断前置门，不更改5cm曲线验收标准。对应门控回归12/12通过，等待新冷启动验证。
