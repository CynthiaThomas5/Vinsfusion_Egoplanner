# #394 N10.4 acceptance 草案与判断器审计

- 对话摘要：[`collaboration/dialogues/2026-10-27-394-n10-acceptance-draft-audit.md`](../../collaboration/dialogues/2026-10-27-394-n10-acceptance-draft-audit.md)
- 轻量证据：[`n10-acceptance-draft-audit-20261027-394.md`](../evidence/n10-acceptance-draft-audit-20261027-394.md)
- 产物 JSON：[`n10-acceptance-draft-audit-20261027-394.json`](../evidence/n10-acceptance-draft-audit-20261027-394.json)

## 改动

- `config/acceptance.json` 从 revision 2 更新为 draft revision 3，增加逐点 `ego_tracking_clearance_budget` 诊断、综合只读采集合同，保持所有候选阈值与 control-effect 声明不变。
- `tools/debug_truth/evaluate_n10_tracking_clearance.py` 输出 v2 identity、run/goal/epoch/map 与 runtime-contract 绑定字段、源输入哈希和评估器 SHA。
- `tools/debug_truth/evaluate_n10_acceptance.py` 校验 tracking budget v2 的身份/哈希；错输入/旧格式/缺数据为 `INSUFFICIENT`；没有几何接受阈值时不判通过。修复脚本直接执行导入路径，确保 identity 不匹配时已观察的直接安全失败仍保留为 `FAIL`。
- `tools/test_n10_acceptance.py` 覆盖 offline-only capture contract、有效/缺失/旧 schema/错 identity/错源哈希的 tracking budget，以及错总身份不抹除直接接触失败。
- #381/#385 新 acceptance 回放与 #391 部分行诊断另存于 `artifacts/runs/n10-20261027-389-archive-reuse/`。

## 验证

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.test_n10_acceptance tools.test_n10_clearance`：26 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/codex-pycache-n10 python3 -m py_compile tools/debug_truth/evaluate_n10_acceptance.py tools/debug_truth/evaluate_n10_tracking_clearance.py tools/test_n10_acceptance.py tools/test_n10_clearance.py`：通过。
- acceptance CLI 对 #381 输出 `FAIL`（原到达失败保留），对 #385 输出 `INSUFFICIENT`；两者 runtime/input identity 均匹配，tracking budget 均为 `INSUFFICIENT`。
- #391 局部回放：tracking budget identity/inputs matched；净空/接触与故障终态为 `FAIL`，未将紧急收尾计作原生 landed/disarmed。
- `python3 -m json.tool config/acceptance.json`：通过。无 ROS 构建需求；没有 SITL。

## 限制与下一步

当前数值仍不能冻结；N10.3 综合校准、六类故障端到端校准、资源/队列容量依据均未完成。下一项实施 N10.3/#395 综合采集的连续图像/IMU 与 receipt observer、地图查询响应 echo 和运行身份检查；缺观测继续记不足且不连接控制。
