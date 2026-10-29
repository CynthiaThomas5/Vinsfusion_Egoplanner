# N10.3/#414 校准准备

新增单变量 EGO regular yaw-rate-cap 校准配置，保留 #412 固定路线与全部现有验收值；新增 patch 0058 默认关闭、ROI 限定、只读的逐融合体素 vote/log-odds trace。Observer 将深度融合和体素更新流持久化为 run-local JSONL，并提供离线 source/event/snapshot 对账评估；缺源/缺数据为 `INSUFFICIENT`，不影响飞行决策。驱动及预启动 identity check 绑定 #414 run id、planner profile 和 0057/0058 patch SHA。

验证：`tools/test_vio_ego_bringup_config.py` 11/11；Python/JSON/shell 语法检查通过；0057→0058 连续 patch replay 与 vendor 文件逐字节匹配。尚无构建或 SITL 结果。详细协议与静态状态见 [#414 preparation](../evidence/n10-integrated-calibration-preparation-20261028-414.md)。
