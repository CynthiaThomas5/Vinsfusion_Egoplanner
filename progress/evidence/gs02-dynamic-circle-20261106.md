# GS02.3动态绕圈初次取证：阶段时序仍需补齐

运行：`hw10-groundstation-20261106T071542Z`；Nano epoch `16192046bb9741c6918df886d84ba741`。用户完成绕圈并确认回到原起点；从Debian正常执行`uav-groundstation experiment-stop`，Nano/Debian原始数据已归档于`artifacts/runs/hw10-groundstation-20261106T071542Z/`。24项`RUN-SHA256SUMS`全部通过，校验清单SHA256为`9b33726f70a2e46292528f7ee55786805dff49ef15e2b7bfc50b695f3bce0b97`。估计轨迹图：`artifacts/runs/hw10-groundstation-20261106T071542Z/groundstation/trajectory.png`（SHA256 `cfe5a2b5e1f0519a37ea14c36033673442f84627190aaf32248b7686d55ade0e`）。

## 轨迹与返回

- Recorder记录901个唯一姿态，运行196.626s，含有效姿态的Debian接收跨度140.712s，累计估计路径21.984m。
- `hardware_display`坐标范围：X 4.349m、Y 3.916m、Z 0.638m。起点约`(-0.0118,-0.2005,0.0076)m`，终点约`(0.0520,-0.1551,-0.0110)m`；端点估计差`(+0.0638,+0.0454,-0.0187)m`，模长0.0805m，末端yaw差约-3.97°。
- 这是VINS自身估计的返回差和轨迹范围，没有独立真值或实测圈半径；不能据此宣称绝对尺度/精度合格。Z方向0.638m变化可能来自真实手持高度变化或估计误差，现有证据不能区分。
- 相邻有效轨迹接收间隔P95/P99/最大值为0.437/0.900/1.599s，其中3次超过1s。该路径流没有复现HW10-VIEW-032记录的16.166s空窗，但1.599s最大间隔仍需解释，且不等于RViz实际渲染帧时序。

## Nano采集、VINS与relay摘要

- Nano localization日志有142个有效TRACKING观察，覆盖约144.8s；另有启动预热观察。`experiment-stop`先停止VINS，随后记录一次`propagated_receipt_stale`并完成正常owner收尾，这是停机边界状态，不计作运动期间失效。session退出记录`px4_outputs=not_started`。
- 左右目源频率约14.999Hz，最大源间隔66.704ms、最大接收间隔109.5/109.2ms，最大source age 336.5/338.3ms。IMU约193.14Hz，最大源/接收间隔310.0/319.0ms。
- VINS optimized约6.324Hz，最大源/接收间隔400/427ms，最大source age 569.5ms；propagated约190.2Hz，最大源/接收间隔320/311ms。965条solver耗时中位数58.39ms、P95 93.36ms、P99 118.61ms、最大136.21ms。
- Nano视觉relay最终计数：image 613、points 921、history 261、camera 918、body 2605；relay统计文件没有逐条接收间隔。Debian最终状态快照只有停机时刻：decode errors为空，clock uncertainty约1.11ms；各通道source age最大约0.440s、transport age最大0.057s。快照中视觉计数低于relay最终计数，无法仅凭终态计数区分采样时刻差、source-age过滤或传输缺口。

## 结论与未完成项

本次确实取得了用户确认回点的动态路径和完整Nano原始日志，轨迹估计首尾差约8.1cm；VINS在运动采集窗口的health观察持续有效。路径接收最大间隔约1.60s，未看到16.166s路径空窗。**GS02.3仍未通过**：旧显示问题涉及双目图和3D轨迹，当前Debian只保存了一份终态视觉快照，不能把运动期间relay逐条到达、Debian解码发布和RViz渲染分开判定，也不能判定计数差的原因。

为下一次验证增加低频Debian状态时间序列和逐条视觉relay接收事件记录：快照含Nano→Debian时钟偏移/不确定度、VINS freshness/stream统计、视觉各通道source/sent/PC-received/PC-processed时间；事件文件只存每条视觉消息的kind、epoch与时间戳，不保存图像/点云payload。代码先更新到迁移overlay并在Debian固定镜像上通过目标测试，再运行同样的VINS-only动态绕圈；目标仍是区分Nano处理、relay/传输、Debian接收/解码与用户所见显示停顿。

本次未启动map/planner/EV/PX4控制、未武装/起飞、未修改固件或参数。实验停止后Nano perception和sensor owner均清空、相关进程退出、`rmem_max=212992`恢复；Micro XRCE-DDS Agent仍active于CH340/TELEM1。

后续带逐条时序记录的第二次动态圈发现Debian接收端约20秒视觉积压，分段数据和归因范围见[显示链路证据](gs02-display-pipeline-20261106.md)。该证据说明首次圈未复现032路径空窗不足以判显示链路通过。
