# N08 #244 慢回程与 compute-only

- 新增 decoupled slow vertical return N05 profile：只将 stage 15 垂直回程由 7s 延长至 20s。`tools.test_preflight_scan` 33 项通过，shell/JSON/diff 检查通过。
- Run 完成 16/16 stages；N05 after/post-release/current-area 在线与离线准入接受，同身份。support helper 的 fresh DISARMED 错误原样保留，独立状态读回解决 monitor-required。
- compute-only readiness 和专用 evaluator 12 项通过。没有 XY 或制动。
- stop-corridor 证书因 launch 用 `n08_low_speed_calibration.json`（0.15m/s）而非要求的 `n08_low_speed_vector_cap.json`（0.075m/s）拒绝；低速速度／地图几何证书仍未通过。
- fresh PX4 状态 DISARMED、landed/at-rest，bridge LANDED/control-disabled，fixture absent；容器 exit 0。

详见[报告](../evidence/n08-slow-return-compute-only-20261024-244.md)和[机器证据](../evidence/n08-slow-return-compute-only-20261024-244.json)。
