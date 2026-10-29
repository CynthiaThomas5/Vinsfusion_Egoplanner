# N08 #292：snapshot 前刷新 MapStatus

## 修改

`tools/run_n08_braking_trial.py::capture_snapshot()` 现在先等待 snapshot service，再通过 ROS executor 处理一条服务等待之后收到的 MapStatus，然后检查 epoch/map identity、reset acknowledgement、input readiness 和原 0.5 s 状态新鲜度门。snapshot 重试期间仍逐次检查这些条件。identity 改变、门关闭或状态未及时刷新都会拒绝，不接受旧 snapshot，也不改变任何速度或安全阈值。

新增 ROS snapshot admission 回归：覆盖服务等待造成旧缓存过期后正确等待新状态，以及服务等待期间身份确实变化时在请求 snapshot 前拒绝。

## 验证

- `bash tools/project.sh test`：348 项通过；navigation-adapter integration 通过；退出码 0。
- `source /opt/ros/jazzy/setup.bash && source install/local_setup.bash && PYTHONDONTWRITEBYTECODE=1 python3 tools/ros_tests/test_n08_trial_snapshot.py`：8 项通过。
- 对 runner 与专项测试执行 Python `compile()` 语法检查：通过。

这次改动仅涉及运行期 Python 与对应 admission 测试，没有改动编译型代码。冷启动 #292 的 N05、preflight、mission admission 和真实 motion-cancel 飞行验证仍待完成；代码回归通过不代表 N08 飞行出口通过。
