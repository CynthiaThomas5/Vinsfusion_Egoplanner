# #294 修复高频 EGO 终端参考确认

## 目标

修复 #293 `cancel_stop_spline_or_measured_hold_timeout`。完整 N05 及 mission 准入通过后，#293 真实运动中取消与停止样条证书通过，但 native runner 未累计 stop hold。

## 诊断与改动

实际 run 的 stop spline 终点 sim `381.344031495 s` 后有 3,578 条稳定 terminal `READY` 命令，速度／加速度为零，source 间隔约 8 ms；PX4 local-position 速度门样本连续达 21.032 仿真秒。原判据每轮只看最新两条，并要求间隔 50 ms，正常高频样本导致始终不满足并重置保持计时。

现在检查覆盖最近至少 50 ms 的整个命令窗口；要求 same goal/epoch/trajectory、允许的终端 flag、终点位置稳定、速度与加速度零。新测试验证 8 ms 稳定流通过，50 ms 窗内任一运动样本拒绝。没有放宽速度、健康、地图、stop hold 或 landing 门限。

## 验证和交接

- `bash tools/project.sh test`：356 passed，navigation-adapter integration passed。
- 记录：[#293 run failure](../evidence/n08-cancel-stop-terminal-window-timeout-20261026-293.md)、[#294 fix](../evidence/n08-cancel-stop-terminal-window-fix-20261026-294.md)。
- 新冷启动 #294 仍需完整 N05 扫描、40 s 只读 preflight、mission current-area 准入、motion-cancel 实测、正式 3 s native hold、destination landing 和 independent evaluator；未执行前不计 N08 pass。
