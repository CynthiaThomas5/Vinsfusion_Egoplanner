# GS02.3静止网络基线与Wi-Fi省电对照

目的：在Nano和Debian均无VINS/relay/viewer会话时，检查动态run中Nano→Debian reader长滞后的网络背景，并单变量检验Nano `wlan0`省电是否显著增加Nano发起连接的RTT。所有ICMP样本各100个、间隔200ms；无飞控控制流量。省电对照后恢复Nano原设置。

## 结果

| 发起端→目标 | Nano省电 | 丢包 | 平均 RTT | P95 | 最大 |
|---|---:|---:|---:|---:|---:|
| Nano→路由器 `.154` | 开 | 0% | 3.742ms | 10.100ms | 21.314ms |
| Nano→Debian `.223` | 开 | 0% | 56.462ms | 103.000ms | 121.061ms |
| Nano→路由器 `.154` | 关 | 0% | 3.053ms | 5.230ms | 23.116ms |
| Nano→Debian `.223` | 关 | 0% | 52.407ms | 107.000ms | 139.161ms |
| Debian→路由器 `.154` | — | 0% | 2.883ms | 4.670ms | 12.098ms |
| Debian→Nano `.186` | — | 0% | 6.472ms | 14.400ms | 38.923ms |

Nano `wlan0`连接5GHz网络、信号约-45dBm、协商速率867Mbit/s；其省电关闭后，Nano→Debian P95和最大RTT没有改善，不能把Nano省电作为修复。对照结束已核实`Power save: on`恢复。Debian无线驱动为`iwlwifi`，模块参数`power_save=N`；NetworkManager连接配置为`default`。静止采样期间Debian无线接收无错误/丢包计数增长。

## 判定与限制

低负载ICMP显示Nano→Debian方向比到路由器和反向Debian→Nano明显更抖，但没有丢包。关闭Nano省电未产生改善；Debian当前驱动状态也不支持简单归因于其省电。ICMP RTT是往返测量，不能等同于视觉SSH/TCP单向传输时间。后来使用真实静止VINS/双路relay运行时，Debian reader延迟P95为约26–74ms、最大约101–165ms，未出现长空窗（见[静止全链路证据](gs02-static-live-20261107.md)）。

因此，这一基线未解释动态run中13.2–20.6秒的send-to-reader滞后；不修改网络持久配置。尚缺动态运行时TCP重传/资源时间线和RViz实际paint记录，GS02.3仍未通过。

测试时Nano系统时间显示为2024-06-18，`NTP=no`、`NTPSynchronized=no`；Debian为2026-11-06。静止全链路入口用run内时钟探针估计偏移并用于延迟计算；本次没有校准或修改Nano系统时钟。原始网络日志的SSID、AP/MAC标识已脱敏，位于`artifacts/runs/gs02-network-baseline-20261107/`；`SHA256SUMS` 5项通过，清单SHA256 `06d94db3950461d9209a543ce7810ec72be32f9e36db621e02956578326b972f`。
