# P2 EGO pose 接收停顿诊断与 QoS 对照

日期：2026-10-17。对话摘要：[2026-10-17-011-p2-ego-pose-receipt-diagnostic.md](../../collaboration/dialogues/2026-10-17-011-p2-ego-pose-receipt-diagnostic.md)。

- 修改：新增 EGO patch 0013，在隔离第三方源码副本中记录 GridMap depth 与 pose 单路接收数／最后 source stamp；新增 patch 0014，将 PoseStamped reader history 从25提高到100作对照。vendor 源树未修改，两个 patch 分别 byte-exact replay 并在 Jazzy overlay 各构建5/5包。
- #29：修正 session namespace 后，VINS 当前 epoch 节点及三个预期 publisher endpoint 正常，depth READY、定位 TRACKING、397组 EGO 配对输入；40.059 s窗口仍有42条 timeout。steady-clock callback约0.98–1.30 ms、occupancy timer约49–51 ms、fusion约3–4.5 ms。首个短组与0.429 s pair gap一致；后续一组则 EGO sync 计数停在400；独立探针仍收到后续配对话题。
- #30：40.032 s无故障窗口记录314组配对输入、map峰值1786、无窗口内 timeout；仅为一次重复观测。窗口后另有5条 timeout 与60 s relay wall-time期限相关。
- #31：60 s probe 与60 s depth relay期限重叠，relay 先于 probe 收尾停止转发，导致 depth_stale；作为夹具时限错误排除。
- #32/#33：80 s relay配合60 s probe，scheduled source fault 90 s 未激活。#32在三个窗口内阶段看到 EGO depth receipt count前进而 pose receipt/sync count停住，独立 subscriber 同时收到该话题后续 pose；这些阶段有19、50、46条 timeout。另有一段0.462 s pair gap。#33在 reader history=100 后再次看到两段相同现象，共49条窗口内 timeout；该窗口的独立配对间隔最大0.297 s。timer仍约50 ms，callback不到1 ms，fusion约3–4 ms。
- 决定：排除 occupancy timer/fusion overrun作为已测时段的主要原因；当前现象指向 EGO 内 pose-reader 接收／交付间歇停顿，但 RMW、executor、DDS queue 或其他来源尚未区分。patch 0014 不作为已接受生产修复；`0.4 s` timeout 与 `ground_height=-0.15 m` 继续标记 PROVISIONAL。
- 验证：`bash -n` 检查 runs #29–#33；patch 0013/0014 replay 与文件对比；对应五包 colcon build exit 0；详细输入、timeout 分组和原始 SHA256 在 [P2 interval evidence](../evidence/p2-ego-input-interval-diagnostic.json)，构建日志在 [P0 diagnostic build evidence](../evidence/p0-ego-map-timeout-diagnostic-build.json)。
- 局限与下一步：patch 0013 的重复 depth subscription 可能增加运行负载；目前无 controller、PX4 或 actuator。下一步检查 EGO订阅 callback group、Fast DDS message-lost/QoS 事件与发布端交付，再用不重复订阅深度图的观测方式复测。根因查明后再重复 no-fault 与活动 stale；不据此冻结 timeout阈值。
