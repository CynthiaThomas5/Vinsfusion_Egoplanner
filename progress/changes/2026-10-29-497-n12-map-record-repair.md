# #497 N12 目标前MapStatus输出修复

关联对话：[记录](../../collaboration/dialogues/2026-10-29-497-n12-map-record-repair.md)。

#496污染YAML导致目标前driver退出，未起飞/发goal；独立地面读回安全后停止归档。新外部release仅在ros2 topic echo /mapping/status --once添加支持的--no-lost-messages选项并保存stderr。真实ground输出已解析并匹配epoch，shell语法/Python编译通过。13项绕行判断器验证从未改源码版本承接；runtime和验收配置仍原哈希，任务请求驻留仍5sim秒。新冻结清单位于artifacts/runs/n12-20261029-497-clean-map-record/release/freeze-inventory.json。当前正式0/3，#494失败与#496启动失败保留。下一#498独立GUI正式冷启动。
