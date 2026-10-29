# #259 专用执行器复用快照限时等待协议

关联[对话摘要](../../collaboration/dialogues/2026-10-25-255-n08-callback-coherence.md)。修改 `tools/run_n08_braking_trial.py`：保存服务拒绝reason，沿用既有compute-only的三类瞬态拒绝与2秒截止；身份、深度pose门、源龄原规则不变。新增 `tools/ros_tests/test_n08_trial_snapshot.py` 六项测试。细节与SITL证据见[#259](../evidence/n08-trial-snapshot-contract-20261025-259.md)。

#258在enable之前拒绝，没有制动数据；#259只读地面复现并验证协议，安全停止。#260重新扫描／执行测量。未改速度／地图门限，未将重试成功算制动通过。
