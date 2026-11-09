# HW02.3 单次 SDK 复位恢复试验

日期：2026-11-02（工作站）；Nano 日历仍为 2026-10-18，未调整时钟。

**结论：本次当前设备的 IMU 零帧已恢复，HW02后续出口也已补齐。** 复位前 SDK 8秒直采为0/0，唯一一次目标设备 `hardware_reset()` 后为 accel806/gyro1585；ROS 60秒采集和一次不加复位的正常停止/重启20秒均持续出样。这支持设备/SDK采集状态可通过复位恢复，尚不能确定底层根因或保证未来开机不复发。用户随后报告相机静止放在桌上、镜头水平向前；当前采样支持静止重力方向与光学轴约定一致。后续尺量约320mm与同目标中心ROI中位数324mm数量级相符，HW02全部出口通过；详情见本报告末尾。

## 授权、身份与唯一变量

- 用户在“一次SDK设备复位，先检查原始IMU，再检查ROS”的方案后明确要求“测试一下，看看能不能解决”。本次仅执行一次API设备复位；未物理拔插、未重启Nano、未改固件或循环reset。
- 相机 API serial `243622073269`、ASIC serial `243323065857`、固件 `5.17.3.10`；USB连接5000M。
- SDK2.58.1及HID-hold/sensitivity库与前轮相同，SHA256 `a72cc3c5030be54ee532347d10a40b3839535bc79b2b4709d10d452c370b69f9`；wrapper3.2.3和相机配置不变。ROS会话实际库映射再次由已有入口检查。
- 探针只读复用 `/home/jetson/realsense_debug/realsense_imu_probe_selectable_sdk2581`，SHA256 `ee957d485cac1f5da19f1d7da90c7c74c9d714c6879ca81f6d535da7100c728e`；reset程序为同目录 `realsense_reset_sdk2581`，SHA256 `5fcf565fc8245a4a2d7816d66049df4f5739bc8720c585e7af7d6831126a47fa`。已读取其selectable源程序，按serial匹配后调用 `device.hardware_reset()`。没有修改旧目录。
- 软件/接线/参数不变；假设为Motion Module初始化或采集状态异常，唯一主要变量为一次SDK设备复位。执行前USB设备节点及所有映射到ASIC serial的视频节点均无进程占用。

## 命令与结果

SDK命令在Nano执行，前后均使用相同库和参数：

```bash
export LD_LIBRARY_PATH=/home/jetson/realsense_debug/sdk2581-hid-hold-sensitivity/lib
/home/jetson/realsense_debug/realsense_imu_probe_selectable_sdk2581 both 243622073269 100 200
# 仅在前测结束、占用检查通过后执行一次：
/home/jetson/realsense_debug/realsense_reset_sdk2581 243622073269
# 等待设备可枚举，再执行相同的8秒探针。
```

- 前测：`accel=0 gyro=0 bad=0`，exit5。
- reset：exit0，输出serial/固件与目标一致；随后25秒轮询未见USB devnum变化（始终3），同serial枚举成功。只能报告API调用成功和设备保持可见，不能声称观察到了USB断开/重新枚举。
- 后测：`accel=806 gyro=1585 bad=0`，exit0。

ROS在独立工作区执行：

```bash
cd /home/jetson/D435i-VINS-EGO-ROS2-hardware
HW02_RUN_ID=hw02-20261102-imu-reset01 bash tools/hardware.sh sensors start
# source Foxy、旧wrapper overlay及本工作区install，固定SDK库和原FastDDS配置后：
ros2 run uav_sensor_interface hw02_sensor_capture --duration-s 60 --output artifacts/runs/hw02-20261102-imu-reset01/sensors-after-60s.json
bash tools/hardware.sh sensors stop
# 随后以 hw02-20261102-imu-reset01-restart20s 启动同一配置，采20秒再stop，未再reset。
```

| 指标 | 复位后60秒 | 正常重启后20秒 |
| --- | --- | --- |
| 实际采集时长 | 60.001秒 | 20.002秒 |
| IMU消息数 / header速率 | 11924 / 199.798 Hz | 3919 / 199.327 Hz |
| IMU非单调间隔 / 非有限值 | 0 / 0 | 0 / 0 |
| IMU最大header间隔 | 19.985 ms | 20.001 ms |
| IMU源龄P95 / max | 16.41 / 30.82 ms | 17.67 / 32.21 ms |
| IMU有限值比例 | 100% | 100% |
| 原生/米制深度帧数 | 898 / 898 | 298 / 298 |
| 深度stamp逐帧保留 | 是 | 是 |
| `force pause`日志数 | 0 | 1 |
| libusb EAGAIN日志数 | 40 | 41 |

60秒两路IR各898帧、14.9998 Hz、最大间隔66.752 ms；898对完全同戳且无未配对帧。深度原生16UC1与32FC1各898帧，同为14.9998 Hz，转换后源龄P95 40.40 ms；中心原始中位数1361mm，米制1.361m，仅作数值转换观测，未替代实测平面比较。

60秒加速度均值为 `[-0.000576, -9.866099, -0.152912] m/s²`，模9.867284 m/s²；20秒重启复验均值为 `[-0.000398, -9.866456, -0.150317] m/s²`，模9.867601 m/s²。specific-force向量在两个会话都近似沿 IMU optical frame 的 `-Y`（与重力加速度方向相反，约0.888°和0.873°），两次单位方向差0.0151°。重力方向数据可重复观测。用户随后报告相机静止放在桌上、镜头水平向前；在该物理姿态下，specific-force沿光学`-Y`与静止重力方向相符，HW02静止重力方向核对通过。此结果不等于IMU偏置标定或IMU到机体/rig的完整外参标定；静止偏置标定不属于本次恢复试验。

重新启动会话在IMU正常输出时仍报告一次force-pause及EAGAIN，说明这些日志单独出现并不足以判定零帧。当前结果没有证明哪个固件/HID/USB机制触发了原异常，也没有证明未来冷开机或长时负载无复发。

## HW02.4 用户姿态与现场深度对照

用户报告当前相机静止放在桌上，脚下有箱子，口述相机与脚下箱子约35cm、离地约65cm、前方桌面约40cm，镜头水平向前；随后澄清前方目标是水平桌面。距离的测量起点仍未明确，且约0.40m的桌前间隔不是自动等同于相机光轴深度。

RealSense D435i optical frame 约定为`+X`向右、`+Y`向下、`+Z`向前；静止时加速度计specific-force与重力方向相反，因此相机直立、光轴水平时应主要沿`-Y`（参见[官方D435i文档](https://github.com/realsenseai/librealsense/blob/master/doc/d435i.md?plain=1)及[RealSense坐标约定](https://github.com/realsenseai/librealsense/wiki/Projection-in-RealSense-SDK-2.0)）。当前20秒样本均值`[0.046724,-9.863085,-0.190142] m/s²`，模长`9.865029 m/s²`，方向偏离`-Y`约`1.137°`；桌面上静止、镜头水平向前的描述与观测相符，静止重力方向检查通过。

对应场景采样 run 为`artifacts/runs/hw02-20261102-scene-check/`，实际20.004秒：IR左右各298帧、15.005Hz、同戳配对298对；深度原生及米制各298帧、stamp保留；IMU3933帧、199.707Hz，有限值100%、stamp单调，最大间隔19.554ms。接收源龄统计有1个负值，作为该短样本的时间域限制记录。

中心20% ROI原生深度中位数`939mm`，米制输出`0.939000m`，ROI有效比例中位数`0.895386`。与口述约`0.40m`直接相减为`0.539m`，但用户已澄清目标是水平桌面，前方水平间隔不能直接当作光轴深度。水平镜头的中心线可能高于桌面；ROI可能测到后方背景。采集器未保存图像负载，不能确定桌面是否出现在ROI下半部，也不能据此判断深度转换/相机故障。桌面深度对照出口仍未通过。

完成该水平桌面的深度对照，需将镜头稍向下俯，使桌面覆盖中心ROI，量出相机光学中心到画面中被测桌面点的视线距离，再复采并比较同一区域。该run的`sensors-20s.json` SHA256为`f24ecffeedc34feaeabc119f7a499cda55139c0bdc10f7a1b1da2a5b15e34bccf`，`SHA256SUMS`清单SHA256为`0ebf90d396a5b59a343074eccee3cf60251fcfae06f500fd9e08471c29d24a11`；清单中全部产物已校验通过。结束后无状态文件、相机/转换器进程或目标设备节点占用。

## HW02.4 标定板约22cm近距采样

用户随后将相机放置在水平桌面，并估计前方标定板距离约22cm；用户现说明没有尺子，前述距离只是目测值，不作深度真值。为记录当前近距场景，按固定 serial `243622073269`、原 SDK/wrapper 与配置执行20秒ROS采集；没有reset、参数变化或源代码变化。首次启动后采集shell因错误启用`set -u`而在source Foxy时遇到`AMENT_TRACE_SETUP_FILES: unbound variable`，退出陷阱正常停止相机会话、未生成采集JSON；记录在`artifacts/runs/hw02-20261102-calib-board-22cm/`，不作为传感器结果。去除`nounset`后以`hw02-20261102-calib-board-22cm-retry01`重试并成功。

| 指标 | 20秒采集 |
| --- | ---: |
| 实际时长 | 20.001 s |
| IR左右帧数／配对 | 298／298／298，时间戳完全相同 |
| 原生深度／米制深度 | 298／298，stamp逐帧保留 |
| 中心20% ROI深度中位数 | 347 mm／0.347000 m |
| 中心20% ROI有效比例中位数 | 67.582% |
| IMU | 3923帧，199.437 Hz，有限值100%、单调，最大间隔20.004 ms |

把目测220mm与ROI中位数347mm相减得到127mm，但用户已说明无尺、距离估计不准确；该差值不构成精度误差测量。原生347mm按既有适配器输出0.347000m，298/298戳相同，单位转换与时间传递本次正常。采集未保存图像负载，无法验证标定板是否覆盖中心ROI或正对相机。

官方 D400 系列数据表在640×480下列出D435i Minimum-Z为175mm，故用户口述的约220mm高于该最小距离；但官方Depth Quality工具的平面测试步骤建议目标位于0.3–2m。本次22cm接近近距范围、低于其建议起测距离，不能替代标准距离下的平面检查。数据表同时说明D435i深度零点参考相机前盖玻璃。依据：[D400系列数据表](https://www.realsenseai.com/download/21345/)、[官方Depth Quality工具说明](https://github.com/realsenseai/librealsense/blob/master/tools/depth-quality/readme.md)。

项目与只读旧记录核查未找到当前这块板的已验证尺寸。旧ROS_SEARCH文件`/home/ac/codexworkspace/ROS_SEARCH/.artifact-work/calibration-offline/target_nominal_unmeasured.yaml`列7×5内角点、名义方格25mm，但首行明确注明物理尺寸未实测；SHA256 `b9e5c050347b5e17653fb1ae47d5ffbcb8cecac79dc062b5acd3164103cc74cb`。这只是候选旧标定target，当前实体板身份未确认，不能用来充当物理尺寸真值。用户随后补充“100mm”，但未说明是整板外尺寸、单格边长还是Tag边长，也未提供pattern格数；在当时的22cm采样阶段，该数字不作为尺度真值，平面深度出口仍待独立量距。后续尺量结果见本报告末尾。

IMU均值为`[-0.464738,-9.864368,-0.138565]m/s²`，模长`9.876281m/s²`，偏离光学`-Y`约`2.815°`；该采样全部有限且单调，但源龄有20个负值。日志有1次`Motion Module force pause`和29次libusb EAGAIN告警，IMU仍连续输出。停止后无工作区会话状态、相机/转换器进程或映射到该serial的设备节点占用；ROS CLI仍列出相机topic，但进程/设备检查为空，不将CLI发现状态当作设备仍运行。

运行目录`artifacts/runs/hw02-20261102-calib-board-22cm-retry01/`，其中`SHA256SUMS`已逐项验证；`sensors-20s.json` SHA256 `9bedcf0b11fe67b0abb0ae9bebb7d2e68d492dfe307cc7ef578e6eca2845db0d`，清单SHA256 `64fee3686f599964351f32faccc69e87e316073a80f98810177a8813faa0cb28`。shell中止记录目录`artifacts/runs/hw02-20261102-calib-board-22cm/`也有已验证清单。该采样阶段HW02当时仍为`in_progress`；后续独立量距已在本报告末尾补齐。

## 22cm采样阶段收尾（历史状态）

两次会话均通过已有入口只停止登记PGID；最终状态文件不存在，相机/转换器进程为空，目标USB和映射视频节点均无占用。没有源代码/参数改动，无需重建或复验无关包。

当时已完成HW02.3恢复验证、HW02.4静止重力方向检查和标定板近距采样；因为量距仅为目测，父HW02当时保持`in_progress`。该待办状态已由下方后续尺量复核更新。尚未进行未来冷开机、长期可靠性、VINS、PX4或飞行验收。

## 后续尺量复核与HW02收尾

- 用户用尺再次测量同一目标，镜头至目标约320mm；此前目标采样运行目录为`artifacts/runs/hw02-20261102-target-35cm/`，中心20% ROI深度中位数324mm，深度有效率65.09%，约4mm差值仅说明该测点数量级相符（尺量为约值），不据此宣称1.3%的绝对精度。该复测满足HW02要求的平面深度数量级核对。
- 20.002855秒记录中原生深度298帧，转换输出299帧；298个原生stamp全部存在于转换输出。额外1帧的来源无法由该计数确定；此前60秒采集中原生和转换输出898/898逐戳一致的证据一并保留。
- 复核 run 的SHA256清单已通过：`cd artifacts/runs/hw02-20261102-target-35cm && sha256sum -c SHA256SUMS`。采样结束确认相机、转换器、采集进程及目标设备节点已释放。
- HW02全部出口通过。HW03是依赖顺序的下一模块，但此次用户授权仅到HW02，因此没有启动后续模块。

## 产物与SHA256

运行目录：`artifacts/runs/hw02-20261102-imu-reset01/` 和 `artifacts/runs/hw02-20261102-imu-reset01-restart20s/`；轻量日志已从Nano同步本地，本地另生成分析摘要和各目录的 `SHA256SUMS`。

- 前测 `sdk-before-8s.log`: `6c7a5c885fb87925d8122668add9aa200eeef5fda77b20e36f1f76f368590cbb`
- 后测 `sdk-after-8s.log`: `9380d5f3a5461bb271c1e820c8c130f1ff669e52b8ae9a4c3a49a1c3061b22c9`
- `sdk-reset-result.json`: `0f682d058b168429de0c7d9c504defcbe0ab5425560c15a8e68c630604f2053f`
- `sensors-after-60s.json`: `07ed44d1c8dfa24725670fe460adb004e173e5eec4f979b896337c6c087cd5c0`
- `analysis-summary.json`（含两次静止重力方向对比）:`4088509f8d4b43651a106dcad4da49b0b8abd7c19c123f1f4e300742042f25eb`
- 重启 `sensors-restart-20s.json`: `f3a1117098971b215c0afcb2993ad096888e0e1a2dfbc0042c635c61b6f1a997`
- 重启 `cleanup.json`: `9b1c5350d3d39ec649a2c0150c33726cebb9e41bdc31adb8df176611396a96a0`
