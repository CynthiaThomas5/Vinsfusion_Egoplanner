# 对话摘要：N08 高窗口取消与停车包络（#298）

- #298 N05 6/6、release后 gate、preflight 与 0.50m候选通道准入均通过；mission goal已发送，抵达高窗口监测阶段。
- `motion_cancel_stopping_envelope_not_available` 是新增的到原goal剩余距离>=0.50m门，过严地阻断caller cancel；fail-safe landed/disarmed。无有效取消测量。
- 保留0.50m候选包络的raw-map corridor admission和独立实际停车路径验收；移除remaining-to-goal拒绝。EGO完整stop spline/hold的fresh同身份raw-map证书在PX4执行前仍是强制门。remaining-to-goal只记录为诊断值。
- 362 tests和navigation-adapter integration通过。下一项#299全新冷启动重做0.07–0.09m/s motion-cancel。
