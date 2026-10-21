# P2 EGO pose 接收停顿诊断与 QoS 对照

日期：2026-10-17

- 用户约束：继续 GOAL.md P0–P6；保护现有 staged／unstaged 文件；不推送；不启动 PX4 控制或实机飞行；旧工程只读。
- 确认：run #25–#28 因脚本把 VINS namespace 留在 #24 epoch 而无效；修正后的 #29 当前 epoch graph 正确，但在40.059 s窗口内仍有42条 EGO timeout。steady-clock 读数不支持 timer 或融合耗时过长。
- 诊断：patch 0013 为 EGO depth 与 pose 输入增加轻量接收计数和最后 stamp。#32/#33 中，EGO depth接收计数增长而 pose计数及同步计数冻结；外部只读探针同时收到 `/drone_0_camera_pose` 后续数据。occupancy timer仍约50 ms。patch 0014将 pose reader history 25→100，#33仍复现两段窗口内接收停顿。
- 夹具更正：run #31 的60 s观察超过测试 depth relay 的60 s wall-time寿命，relay结束造成 `depth_stale`，该 run 排除。后续 #32/#33 将 relay寿命设为80 s，并把计划深度fault设在source90 s，窗口内未触发。
- 决定：#23与#30各有一次40 s no-timeout窗口，#24/#29仍有窗口内timeout，#32/#33定位到 EGO pose输入接收间歇停顿但未查明底层原因。`0.4 s` timeout与 `ground_height=-0.15 m` 仍是PROVISIONAL。0014只是隔离实验，不作为已接受修复。
- 待决：EGO内部pose订阅何以漏收独立观测者能收到的消息；需检查 executor callback group、Fast DDS/RMW message-lost与端点QoS，随后重新验证健康输入和活动 stale。
