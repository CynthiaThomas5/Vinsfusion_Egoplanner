# #213 N08 compute-only 准入拒绝

## 任务上下文

继续完成用户指定的 N08 Goal；不复测 N07 既有通过结果。没有 same-run known-free 停止走廊和制动边界前不执行平移。

## 结果

- N05 current-area 准入通过，运行图确认 bridge 的 PositionCommand 输入已隔离；但运行没有 `/navigation/ego_goal` 消息或 READY 曲线。runner 因此失败并按 `operator_disable` 安全落地，未发生横向移动。
- frozen raw map 对 +Y 0.6 m 目标球的离线复算发现 333 个 unknown 体素、0 occupied；目标球最低点高于地面。真实 action-time 服务响应没有记录，因此把它记为强推断。Y 方向扫描显示 +Y 侧未知逐渐增多；离线候选 `-Y 0.4 m` 的同半径目标球是全 free，但尚未实时重验。
- 支撑扫描器未取得足够新鲜的最后 DISARMED 回执，外层按流程留置容器。夹具已移除、落地与在线准入随后确认后才运行 compute-only；飞行结束后容器已停止。

## 下一步

改进 compute-only runner 的 action 终态采集与失败取消清理；用新的冷启动和 -Y 0.4 m 候选重新经过 fresh N05 和目标查询。半径与未知拒绝保持不变；N08 仍未完成。
