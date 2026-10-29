# #292：修正 N08 snapshot 前 MapStatus 刷新顺序

## 目标

解决 #291 在 N08 目标之前的 raw-map snapshot 门禁拒绝，并保留地图 identity 与状态门槛。

## 证据与修改

#291 的 N05 6/6、post-release admission、40.004 s preflight 和 mission current-area N05 均通过；随后 runner 在 `capture_snapshot()` 请求 snapshot 前因 `trial_map_changed_during_snapshot_request` 退出。旧实现先检查缓存状态的新鲜度、再同步等待 service，等待期间未显式处理 MapStatus 回调，且没有把实际 map/readiness 变化写入失败原因。

`capture_snapshot()` 现在先等待 service，再 spin 收到新的 MapStatus 后验证当前身份和 readiness；后续 snapshot 等待/重试仍检查身份、reset ack、input readiness 和 0.5 s 状态新鲜度。状态真的变化仍 fail-closed，错误记录包含 expected/observed identity 或关闭原因。新增测试覆盖等待期间缓存变旧后刷新继续、以及真实 identity 替换后不调用 snapshot service。

## 验证与限制

- `bash tools/project.sh test`：348 项单测及 navigation-adapter integration 通过。
- ROS 专项 `tools/ros_tests/test_n08_trial_snapshot.py`：8 项通过。
- Python runner 与专项测试语法检查通过。
- #291 final PX4 读回与项目容器停止均已完成；其 N08 结果仍为 pregoal fail，不计作执行通过。

## 下一步

启动新冷启动 #292，重新取得同一版本的 N05 6 阶段与 post-release 准入；通过只读 preflight 和 current-area admission 后，执行单段 `single_goal motion_cancel 0.04 0.06`。验收 caller-cancel、替换停止曲线、旧曲线不恢复、真实制动/保持、目标点落地和 PX4 disarmed。N08 仍 in progress。
