# P2 复测脚本 epoch namespace 修正

日期：2026-10-17。对话摘要：[2026-10-17-010-p2-vins-session-namespace-fix.md](../../collaboration/dialogues/2026-10-17-010-p2-vins-session-namespace-fix.md)。

- 修改：发现 run #25–#28 复制脚本里 `VINS_NS` 仍从 run #24 的 `session.json` 读取；修正当前 run 脚本为从 `$RUN/session/session.json` 动态获取 namespace。更新 P2 输入间隔证据、CURRENT、证据索引，并给 run #25/#26 早期记录附更正。
- 根因证据：run #28 `raw-vins/summary.json` 的 discovered VINS node namespace 是 run #24 epoch `183aa722...`；本 run adapter epoch 为 `96633582...`，对应三个预期 VINS topic 都没有 publisher。VINS log 记录的是当前 #28 YAML，但 CLI namespace 参数从错误 manifest 读出。
- 重新定性：run #25–#28 只证明脚本 namespace 错配和 adapter 无输入，不证明 VINS 初始化随机，也不触发 EGO 调度 patch 0012。原先将初始化超时作为 VINS 可重复性问题的判断已更正。
- 验证：#29 脚本通过 `bash -n`；实际 raw graph 发现 VINS 节点和三个期望 publisher endpoints 均在当前 epoch 下，定位 TRACKING。输入区间与 EGO 诊断已并入 [P2 interval evidence](../evidence/p2-ego-input-interval-diagnostic.json)。
- 后续：#29 仍有42条窗口内 timeout，因此不能作为干净基线；patch 0013/0014 的内部接收计数与 QoS 对照详见新记录 [011](2026-10-17-011-p2-ego-pose-receipt-diagnostic.md)。
