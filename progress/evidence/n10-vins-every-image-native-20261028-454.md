# N10.3/#454：每帧 VINS 入队未改善原始误差

在 #449 的隔离可靠输入/原生处理追踪协议上，以同一 #436 MCAP 和原有估计器参数，只将 `inputImageCnt` stride 从 2 改为 1。两个案例均完整接收相同 IMU 39,181 条、左右图像各 4,749 条；所有双目对均进入同步处理，native catch-up drop 为 0，图像队列保守前缀高水位 1/1。报告已更正 `source_pose_rate_differs_by_intended_treatment` 字段：原始输出由 2,364 增为 4,738，但两组共同评估时刻完全相同。

stride1 的运动 RPE10 平移 p95 为 0.068600 m（#449 原参数基线 0.060495 m），目标段位置误差 p95 为 0.117093 m（0.106709 m），保持段速度误差 p95 为 0.015835 m/s（0.015166 m/s）；运动 RPE 与保持速度仍超过原 draft 上限 0.05 m、0.01 m/s，且趋势变差。候选解算 p95/max 为 29.10/36.55 ms，低于原 40 ms预算；特征队列高水位为 3（基线为 1）。未观察到该候选带来精度或门限改善，不部署；其他 draft 指标按同一未经修改的 `config/acceptance.json` 评估。

这是具备完整输入覆盖的离线否定校准，不是飞行或正式验收；未改主 vendor、安装二进制、在线参数和验收数值，没有 PX4/planner。原始回放结果、逐帧输入 trace、候选 binary、构建和复算脚本位于 `artifacts/replays/n10-20261028-454-vins-every-image-native` 与 `artifacts/n10-prepared/n10-20261028-454-vins-every-image-native`。复算指标依据 SHA-256 `7924cd99…b041f2`，draft gate SHA-256 `5ed1ed42…dfa47f`，原 acceptance 配置 SHA-256 `ad6b8b92…c54d99a`。父 N10.3 仍未通过。
