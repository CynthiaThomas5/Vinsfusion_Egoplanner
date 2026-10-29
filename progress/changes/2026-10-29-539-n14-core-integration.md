# #539 N14独立核心验收集成

Goal完成模式。新增config/acceptance_n14.json revision14，继承#521诊断策略但将必需场景改为n14_scene_navigation；N13冻结配置/报告不改。新增tools/n14_navigation_policy.py绑定窄道世界与代码SHA，通用n13_navigation_policy.py仅按显式kind分派，修改前源码快照保存在artifacts/runs/n14-20261029-539-integration。新增evaluate_n14_run.py核对n14启动记录/场景名及GUI/核心结果，prepare_n14_evaluation.py复用共享只读视图链并写独立N14报告；共享管线新增可选工具/报告参数，默认N13行为保持。

验证：106项新旧策略/绑定单测PASS；实际N13归档完整新管线复放errors=[]，不具备N14启动记录，整体INSUFFICIENT，原报告不覆盖；语法编译、project_status、git diff --check通过。产物artifacts/runs/n14-20261029-539-integration与artifacts/reanalysis/n14-20261029-539-negative-pipeline。

未飞行，正式0/3；N14协议/核心场景仍pending，不能假定成功。下一步从N13候选隔离复制，仅部署新世界并逐文件核对，冻结N14协议/运行身份及脚本后启动GUI。仍需三次正式任务和不可通行/未知目标验证。对话collaboration/dialogues/2026-10-29-539-n14-core-integration.md。
