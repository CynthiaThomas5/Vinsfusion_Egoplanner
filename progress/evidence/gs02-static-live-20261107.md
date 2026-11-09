# GS02.3补充静止全链路采样

运行：`hw10-groundstation-20261106T083700Z`，Nano epoch `111a1d788caa42be8fc3d52cb4e8bacc`。从Debian迁移入口 `uav-groundstation experiment-start` 启动，保持设备静止约159秒，再用 `experiment-stop` 正常结束。此run用于收集新增资源采样，用户没有移动，**不算绕圈，也不通过GS02.3动态出口**。

## 接收与定位

- Debian 5Hz状态采样717条，覆盖165.517秒；采样间隔P95 0.257秒、最大0.443秒。视觉事件4479条：body 2151、camera 795、history 223、image 510、points 800。
- 506条状态观察为有效`TRACKING`；8条为启动预热；194条`MISSING`发生在健康状态源启动前及初始化期间；9条`propagated_receipt_stale`位于正常停止边界。静止记录器保存793姿态、168.041秒，最大姿态接收间隔0.525秒。
- 每通道Debian接收间隔P95/最大值：body 0.084/0.188秒，camera 0.250/0.344秒，history 0.674/0.753秒，image 0.310/0.383秒，points 0.255/0.340秒。未出现动态run中的多秒接收空窗。
- 按run内Nano/PC时钟偏移校准，relay发送至Debian reader接收延迟P95/最大值：body 26.5/137.1ms，camera 29.0/121.5ms，history 28.3/100.9ms，image 74.3/149.7ms，points 33.5/164.7ms。时钟偏移估计为75,286,874.300秒，估计不确定度最大1.515ms；Nano系统时钟当时未启用NTP，详见[网络基线记录](gs02-network-baseline-20261107.md)。
- 本地处理队列P95约47–50ms；points/history采样最大约0.304秒，其他通道最大约53–57ms。解码错误0。最后状态样本中VINS为TRACKING，`px4_receiving=false`、`px4_ev_fusion_verified=false`。

## Debian资源与收尾

- 4核宿主负载三项均值的P95为1.31/0.79/0.56；可用内存P50约9.16GB。viewer进程RSS P95约191MB，容器内存峰值约303MB。
- cgroup CPU `nr_throttled=0`、`throttled_usec=0`，memory `oom=0`、`oom_kill=0`。默认无线网卡在采样期间RX错误/丢包为0；TX错误为0且累计丢包计数保持24不变。
- viewer console记录RViz OpenGL 4.6；立体渲染不支持提示不影响当前单目/双目图像显示。屏幕实际paint时间没有采集，因此不能据消息接收代替显示器画面验收。
- `session-exit.json`为`px4_outputs=not_started`。停止后Nano无统一会话、`rmem_max=212992`；Micro XRCE-DDS Agent仍按原状态运行。没有map/planner/EV/control、武装/起飞或飞控改动。

## 判定与限制

Debian入口、相机/VINS、只读relay、视觉reader与RViz在静止条件下完整启动和正常停止；这段采样未复现动态run的长时间reader滞后。它证明静止负载下接收链路稳定，不证明运动期连续，也不能解释此前的20.627秒send-to-reader最大延迟。动态问题需在用户回来后，用同一资源采样复现并让用户观察屏幕，才能继续判定。

原始数据在`artifacts/runs/hw10-groundstation-20261106T083700Z/`，其中`RUN-SHA256SUMS` 25项通过，清单SHA256 `b42f7e2eae06e81fd71f75f5982fa56d195db413146327ad2b27bfd30799e533`。完整摘要见`groundstation/recorder-summary.json`；运行状态及接收事件分别为`viewer-status-samples.jsonl`和`visual-receive-events.jsonl`。
