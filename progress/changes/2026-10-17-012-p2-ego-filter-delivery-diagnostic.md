# P2 EGO filter 接收与交付诊断

日期：2026-10-17。对话摘要：[2026-10-17-012-p2-ego-filter-delivery-diagnostic.md](../../collaboration/dialogues/2026-10-17-012-p2-ego-filter-delivery-diagnostic.md)。

- 修改：新增 patch 0015，在现有 message_filters depth/pose subscriber 上统计接收，并监听对应 RMW message-lost 事件；移除重复 topic 订阅。隔离源码副本 Jazzy 构建5/5包通过，项目 vendor 源码未修改。
- 运行：#34因 imu_stale 无健康定位输入；#35因运行目录缺少 launch 辅助文件未启动；#36定位与深度健康但 reset service 响应丢失，输入门关闭；三者均排除。#37 将 EGO reset service 启动在 mapping adapter 之前，确认服务可见后获得清图确认。
- #37 有效60.026 s：496组同 stamp EGO depth/pose 输出，地图峰值1905，定位 TRACKING、深度 READY。EGO窗口内46条 timeout；首组期间 pose filter 计数停在514、depth计数522→541，最后 pose stamp 41.779 s、depth 到43.594 s。两侧 message-lost 计数均为0，独立观察者在窗口内收到 stamp 到45.508 s 的 pose。配对源间隔最大0.297 s；pose wall receipt 间隔最大1.201 s。剩余6条 timeout 在探针结束后。
- 解释：证据把问题收窄至 EGO pose filter 的间歇接收／交付停顿；没有 RMW message-lost 通知，但这不足以确定具体 executor、DDS reader 或队列原因。patch 0015 仅诊断，不是修复；健康运行仍出现窗口内 timeout，因此不是干净 no-timeout 基线。
- 验证：build #07 五包构建 exit 0；run #37 probe exit 0；脚本 bash -n、证据 JSON 与新 run artifact SHA256 检查、python3 tools/project_status.py、git diff --check 和 git diff --cached --check 均通过。
- 静态复核：EGO main 使用 rclcpp::spin(node)；message_filters 输入和 GridMap timers 未指定独立 callback group。深度回调、occupancy timer 与 reset 共同访问未加锁的 MappingData，直接换 MultiThreadedExecutor 会引入并发风险。#33 的 pose history=100 已在另一构建中试过且仍有停顿；#37 中 occupancy timer 约50 ms、fusion约3.754 ms，单线程本身尚非根因证据。
- 局限与下一步：保持0.4 s与 ground_height=-0.15 m 为 PROVISIONAL；先做不改变共享地图并发语义的 reader/executor 诊断，再决定是否需要加锁和执行模型调整。无控制器、PX4或实机证据。
