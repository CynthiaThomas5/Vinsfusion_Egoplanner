# #473 N11空场协议与覆盖检查

新增docs/protocols/n11-empty-scene.json、tools/n11_acceptance_contract.py及13项有判别力的测试；更新CURRENT/milestones与证据。冻结acceptance、原候选源码/安装均未改。新增检查器在根工作区离线执行，不进入当前冻结飞行候选。

验证：13项unit通过；真实#472归档INSUFFICIENT、#460非空场归档FAIL，均不可计数。python3 tools/project_status.py、git diff --check作最终结构检查；离线源码无需ROS/PX4重建。本轮无SITL/飞行。

未完成：静态墙面raw/inflated采集与几何/分类判断、observer适配、全链路预演。下一项N11.2b；停止原因为本轮有界子项完成，父N11与N11.2均未完成。

[证据](../evidence/n11-applicability-contract-20261029-473.md)；[对话](../../collaboration/dialogues/2026-10-29-473-n11-applicability.md)。
