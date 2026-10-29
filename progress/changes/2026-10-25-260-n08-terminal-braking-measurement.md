# #260 真实末端制动测量与失败交接

关联[对话摘要](../../collaboration/dialogues/2026-10-25-255-n08-callback-coherence.md)。实际运行前向EGO目标成功；返航因map_query_unknown拒绝，native FAIL，终点附近安全落地上锁并停止。数据、指标、运行命令、哈希与限制见[#260证据](../evidence/n08-terminal-braking-measurement-20261025-260.md)。N08仍in_progress。

离线分析器允许计数后折叠完全相同源戳／运动状态的重复参考发布；时间不排序／不改写，矛盾同戳和倒退仍拒绝。新增3项回归（完整制动分析7项、相关N08合计25项）。分析器记录运行时／离线版本哈希；原始数据不改。mission_runtime让失败的execute仍保存独立诊断，保留native FAIL与退出非零，避免返航失败丢掉已取得的前向制动数据。bash -n、相关单元、git diff --check通过。

本轮按用户指定测量后报告范围结束，未将失败整轮或N08标通过。下一项#261先审计返航unknown，不重测N07或已取得速度／前向停车数据。
