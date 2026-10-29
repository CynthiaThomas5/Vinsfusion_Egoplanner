#423 N10 只读观察器信号收尾

- 修复：truth/contact observers 覆盖继承的 SIGINT/SIGTERM ignore；收到请求后在主线程取消订阅、保存部分数据，并将信号停止与安全会话终态分开记录。
- 文件：`tools/observer_window.py`、`tools/debug_truth/record_truth.py`、`tools/record_n09_contacts.py`、`tools/test_observer_window.py`。
- 验证：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.test_observer_window tools.test_n10_truth_observer`（10项通过）；`py_compile` 与目标文件 `git diff --check` 通过。
- 限制：本改动不触碰 #415 当前控制栈；检查时两个记录器已不在运行。当前 bridge/PX4 未满足终态，#391 一次性紧急 disarm 授权已耗用。没有构建或飞行证据，N10.5–N10.7 未开始。
- 证据：[N10-423](../evidence/n10-observer-signal-shutdown-20261028-423.md)。对话摘要：[2026-10-28-423](../../collaboration/dialogues/2026-10-28-423-n10-observer-signal-shutdown.md)。
