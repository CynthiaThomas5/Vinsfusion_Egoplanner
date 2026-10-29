# #500 取消平移RPE数值拒绝条件并恢复N12

关联对话：[用户授权](../../collaboration/dialogues/2026-10-29-500-remove-rpe-limit.md)。

新增config/acceptance_n12.json revision10，唯一数值门限变化为删除translation_p95_max_m；平移量测继续输出。evaluate_n10_acceptance支持该字段缺省时报告OBSERVED，保留旋转比较及支持/缺失数据判定；旧配置含该字段时继续得到原FAIL。新增7项策略测试并运行原验收回归，共44项PASS。

新N12外部协议/评估器冻结；显式列出#498原正式launch记录与协议SHA进行用户授权重评，完整新报告PASS，旧FAIL不改。生产候选runtime仍90fd8dae...；只读评估器和配置身份单独固定，不修改在线源码/参数/binary。#499离线实验停止推进，不部署16迭代。#498复用后N12 1/3；下一#501独立GUI正式冷启动。结构/diff检查在状态写回后执行。
