# N03 深度实际融合连续性

- 用户通过 `codex resume --last` 恢复先前明确授权的 Goal 完成模式，范围为 N03。
- 保留已有工作区改动；仅运行完整 idle SITL 与只读观测，不解锁、不发布目标、不执行轨迹。
- N03 诊断沿用 0.4 仿真秒融合新鲜度门和 adapter 已有队列上限 8；不改健康、规划或控制行为。
- 已决定将球查询服务的 `no_fresh_fused_depth`（待融合输入）拒绝与最近已完成融合的连续新鲜度分开统计。实际曲线准入使用同一 plan_env freshness 检查且允许读取上一完整融合；不因查询采样节奏误判融合间隔。
- N03 已完成：三次独立 idle fresh epoch 通过；一次启动因 `telemetry_stale` 失败并保留；有界深度断流关闭门、reset ack、新 map identity 重建及旧身份拒绝均有证据。静态 idle 结果不替代 N09／正式飞行期连续性。
