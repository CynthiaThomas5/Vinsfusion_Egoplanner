# P2 深度新鲜度健康门

- 对话摘要：[P2 深度健康门](../../collaboration/dialogues/2026-10-16-018-p2-depth-health-gate.md)
- 文件变化：新增 `uav_interfaces/msg/DepthHealth`、`uav_mapping` 的 `depth_health_monitor`、深度门配置和纯逻辑测试；更新深度故障 relay 文档、架构／接口契约、README、CURRENT、P2/E 证据索引。该包只发布深度输入健康，不生成占据地图。
- 构建：Jazzy 派生环境新目录构建 `uav_interfaces` 与 `uav_mapping`，再按最终源码增量构建通过；命令和日志哈希见[证据报告](../evidence/p2-depth-health-gate.json)。
- 测试：`python3 tools/test_depth_gate.py`，4 项通过，覆盖配置、启动过期、有效布局、断流恢复和时间戳回退锁定。
- 回放：在 ROS domain 111、112 分别冷启动 relay、monitor、probe 和 bag player。两轮均在 source window `[3.166s, 8.166s)` 内丢弃深度，门控在故障期间由 READY 转为 STALE，首次恢复帧到达后回到 READY。精确 stamp、wall transition、计数及 SHA256 见[证据报告](../evidence/p2-depth-health-gate.json)。
- 调试及失败尝试：0.5秒探索阈值与捕获 bag 的不均匀帧间隔产生额外 stale/ready；最终暂用1.0秒阈值，但仍为 PROVISIONAL。启动时没有输入按2秒 startup timeout 报 `depth_missing` 是预期行为。首次 `SIGTERM` 关闭 monitor 出现 `ExternalShutdownException`，已补处理；一次单测夹具漏了 status period，已修正后4项通过。中间运行报告复用并覆盖了同名临时结果，已在对话摘要如实记录；正式证据引用独立的 `...-02` 目录。
- 局限：`READY` 仅说明最近收到结构匹配、递增时间戳的图像；未检查像素有效比例或地面真值精度。当前没有地图生成器消费该状态，也未证明旧地图清理、EGO 停止、PX4 退出或降落行为。录包报告2344条传输丢失，只作为故障注入输入，不可用于频率或完整性验收。
- 下一步：实现与 VINS epoch 和深度采样时刻位姿对齐的实际占据更新；让 stale/epoch 变化使地图失效并阻止规划，再接入真值调试链路测试。
