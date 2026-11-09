# GS02.3第二次动态圈：接收延迟分段证据

运行：`hw10-groundstation-20261106T074153Z`，Nano epoch `8194ca98586c49edb15a76ae91a6cf33`。用户完成绕圈并告知返回。由Debian `uav-groundstation experiment-start/experiment-stop`运行并正常收尾。原始Nano日志、Debian时序和轨迹在同名`artifacts/runs/`；`RUN-SHA256SUMS`共26项全部通过，清单SHA256 `78f374fbc9afa9140a6176e437e288c668c7ecb5e0ad6af7ef6dd4fafff93cde`。

## 轨迹

- 记录1176个唯一姿态，姿态接收跨度174.134s，累计估计路程21.303m；硬件显示坐标范围X/Y/Z为4.533/3.779/0.647m。
- 首尾位置差(-0.0656,+0.1068,+0.0257)m，模长0.1279m，估计yaw差+2.97°。没有独立真值或实测圈半径，只报告估计轨迹和回点差，不宣称绝对尺度/精度。
- 路径接收间隔P95 0.275s，最大8.302s，3次超过1s；最大空窗位于sampler启动后约70.37–78.67s。轨迹图为`groundstation/trajectory.png`，SHA256 `14236bc1b46fea43ee442cd6dfa4b120f6d1bb9dfb4a42760fbf7b234fe15bcc`。

## Nano采集/VINS/relay

- Nano `localization.log`有178条约1Hz健康观察，跨度181.71s、最大观察时间间隔1.056s；175条为有效TRACKING，另两条为启动预热，一条`propagated_receipt_stale`位于VINS停止边界。左/右相机每秒计数增加14–16，优化位姿每秒增加3–9，propagated每秒增加151–210；运动期间没有对应8秒或20秒输入空窗。
- run末端流统计：双目各2727条（源频率约15Hz）、optimized 1209条（约6.65Hz）、propagated 34914条（约192Hz）、IMU 35403条（约195Hz）。
- Nano relay记录的消息`sent_wall_s`无超过1s的相邻间隔：body/camera/history/image/points的最大间隔分别为0.102/0.481/0.809/0.382/0.469s。源戳到Nano发送的最大龄均不超过0.631s。Nano最终计数与Debian收件事件计数相差不超过7条，差异符合两个终态统计文件采样时刻不同；收件事件没有明显永久丢失证据。

## Debian接收/本地处理

- 5Hz状态文件有995条、覆盖227.431s，采样间隔P95 0.258s、最大0.484s；全程`visual_decode_errors`为空。各通道PC读取回调的最大相邻间隔：body 7.211s、camera 7.719s、history 8.061s、image 10.114s、points 7.211s。
- 用Nano/PC时钟偏移（不确定度最大1.666ms）校正后，relay发送至Debian Python reader读取的延迟P95/最大值：body 10.245/13.355s、camera 10.335/13.387s、history 9.912/13.215s、image 17.209/20.627s、points 10.333/13.386s。
- 同一窗口视觉处理计数出现长平台：image 29.06s、body 25.42s、points/camera约22.70s、history 24.29s。VINS日志reader也短暂落后，显示新鲜度门在约69.9s和73.4s把状态标为stale；最旧pose source age约11.0s。随后积压排空，数据计数继续增长。
- 收到消息后的本地排队时间P95约0.048–0.051s，最大不超过0.067s；与10–20秒差异相比很小。接收延迟图见`groundstation/display-pipeline.png`，SHA256 `2d3e1d662644b1bfd2d04a2263aa3a4410af543ae6bf11e0328bcebea95d2808`。

## 判定与界限

这次的停顿链路已从“位置未知”缩小到**Nano relay生成消息之后、Debian用户态reader读到消息之前**。Nano相机/VINS、健康记录和relay发送节奏没有对应长停顿；Debian多路SSH输出在同一窗口读到旧消息并集中补收，本地解码/处理队列在收到后很快。证据不支持把该现象归因于EKF停止融合或VINS轨迹漂移。

尚不能区分局域网/TCP重传或SSH流控，与Debian viewer/系统线程调度造成的读取延后；本次没有运行期CPU/GPU/cgroup/网卡重传统计，也没有RViz实际paint时间线/屏幕录制。`experiment-stop`按当时流程移除了viewer容器，没有保留其console log；`work`账户也无权限读取对应内核journal。因此不能声称根因已完全确定或已修复，GS02.3与GS02保持未通过。

这轮仅运行纯perception/VINS/可视化：`session-exit.json`为`px4_outputs=not_started`；Debian各状态样本均未收到PX4数据。没有map/planner/EV/control、武装/起飞或飞控固件/参数修改。收尾复查Nano无unified session及VINS/localization/relay进程，`rmem_max=212992`；Micro XRCE-DDS Agent active于CH340/TELEM1；Debian viewer容器已停止。

后续已加入host/cgroup/网卡资源观测和停止时保存viewer console log，并在Debian固定镜像通过目标测试；这些字段尚未在动态运动run中采集。实现、证据和完整第二圈数据已同步进freeze01迁移overlay，release 380项与run 26项SHA256均通过。用户回来后再做短慢速动态回归，将reader延迟与容器资源、Linux网络计数、屏幕停顿对齐。若未复现或仍不能区分，保留该出口未通过，不以轨迹回点代替实时显示验收。
