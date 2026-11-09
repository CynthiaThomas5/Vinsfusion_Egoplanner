# GS02.3静止全链路与网络基线诊断

用户表示将外出，要求先完成不需要其辅助的部分；继续原GS02 Goal，不要求移动或屏幕观察。范围仍为GS02.1–GS02.4，不授予武装/起飞权限。

完成的独立工作：

- 在Nano无统一session、Agent独立运行的状态下，测试Nano→Debian、Nano→路由器及Debian→Nano低流量ICMP；临时关闭Nano Wi-Fi省电做单变量对照后恢复。未改持久网络设置。
- 通过Debian现有`experiment-start`运行约159秒静止纯perception/VINS/视觉采集，取得状态、视觉接收、宿主/cgroup/网卡资源和viewer console数据；未移动、未启动EV/control。随后由`experiment-stop`正常结束。
- 读回并校验Nano与Debian运行数据，确认Nano无统一session、`rmem_max=212992`，Agent继续active于CH340/TELEM1；Debian viewer已停止。

结论：动态run长停顿未在静止真实全链路中复现。Nano省电开/关下空闲Nano→Debian RTT差异不显著，Debian无线驱动亦显示省电关闭；目前没有证据支持写入持久网络修复。静止/网络run及上下文已同步到freeze01 overlay，目标端release 380项、run 25项和网络5项清单，以及结构/check/status检查通过。GS02.3仍未通过：动态运行期的长滞后根因和RViz屏幕paint尚未判明，后续需要用户回来协助短时移动并观察屏幕。静止与网络证据、原始数据和校验值见对应progress/evidence与artifacts/runs目录。
