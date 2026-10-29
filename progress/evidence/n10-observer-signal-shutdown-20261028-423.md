#423 — 只读观察器可控中断

## 目的

修复 #415 中 truth/contact 只读记录器继承父 shell 的 `SIGINT=SIG_IGN` 后，收到停止请求仍不退出、无法写出部分记录的问题。该修复只影响后续启动的观察器脚本，不改变飞控、任务、起飞门、取消或降落行为。

## 改动与验证

- `tools/observer_window.py` 为 `SIGINT`/`SIGTERM` 安装只记录请求的处理器；主线程随后正常取消订阅并写报告。停止原因区分安全终态、外部信号与 wall timeout。收到信号本身不会被解释为 landed/disarmed。
- `tools/debug_truth/record_truth.py` 在外部信号后写出已采样的部分 truth/cadence 记录，并明确 `safe_session_terminal_observed=false` 与 `observation_stop_reason=signal_requested`（除非在停止前独立观察到安全终态）。
- `tools/record_n09_contacts.py` 在 readiness 阶段中断时写出未就绪/不完整报告；采集中断时写出已收到的部分 contact 事件及终态标记。
- 新增子进程回归：子进程继承 `SIGINT=SIG_IGN` 后仍能接收停止请求、退出并落盘 `signal_requested`，且安全终态保持 false。

验证命令及结果：

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.test_observer_window tools.test_n10_truth_observer
Ran 10 tests — OK

PYTHONPYCACHEPREFIX=/tmp/n10-20261028-423-pycache python3 -m py_compile tools/observer_window.py tools/debug_truth/record_truth.py tools/record_n09_contacts.py tools/test_observer_window.py
passed

git diff --check -- tools/observer_window.py tools/debug_truth/record_truth.py tools/record_n09_contacts.py tools/test_observer_window.py
passed
```

## 身份与范围

工作区 SHA256：

- `tools/observer_window.py`: `770b3f45fb96b666954da68fc3472a92b1d9b228d51c6c87a3c84d38ca3d7346`
- `tools/debug_truth/record_truth.py`: `2988d7879c0bf84dfba8b9e731cf72c1382963715cfd6cf9762e936cc398209f`
- `tools/record_n09_contacts.py`: `b583a843b109ead4d0b72af31ba08493fa86a560f0129a3f713b3d18dc8e16a0`
- `tools/test_observer_window.py`: `0257738c289ca6d15c9780f165758610817f3e4abb5a224eee7113567b39bfae`

当前 #415 container 检查时，truth/contact 两个记录器进程均已退出；未修改运行中的 observer、控制栈或配置。#415 的已锁定运行输入和原始运行记录不变。以上验证是离线代码测试，不构成 PX4 终态、飞行、构建或 N10.5/N10.6 证据。

## 未完成

#415 仍停在 bridge `LANDING`、PX4 armed failsafe `DESCEND`，没有独立 landed/disarmed/control-disabled/zero-control 读回。#391 的一次性紧急 disarm 授权已使用，不能复用；本次未发送控制命令。N10 仍为 `in_progress`，N10.5–N10.7 尚未开始。
