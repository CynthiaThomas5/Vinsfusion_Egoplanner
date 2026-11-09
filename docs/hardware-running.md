# Nano 分层地面启动

运行前先读取 [`progress/CURRENT.md`](../progress/CURRENT.md) 和实时 `hardware.sh status`。本页保留分层启动操作说明；按日期标记的 HW10 章节是当时实验记录，不代表当前设备状态。

在 `/home/jetson/D435i-VINS-EGO-ROS2-hardware` 干净shell运行。真实rig仍未装机合格；用户明确允许HW09跳过HW08依赖，限定关闭PX4输出的地面计算。HW08、真实EV融合与飞行资格不因此通过。

```bash
bash tools/hardware.sh start sensors
bash tools/hardware.sh status
bash tools/hardware.sh stop
# 选择一个层级启动；已有会话先停止，不能叠加重复启动。
bash tools/hardware.sh start perception  # sensors + VINS/localization
bash tools/hardware.sh start plan        # 上述 + map/EGO/traj_server/nav
bash tools/hardware.sh start full-load --run-id hardware-full-load-example --measure-seconds 300
bash tools/hardware.sh status
bash tools/hardware.sh stop
```

`--measure-seconds` 是显式负载测量指令，会在真实定位/地图就绪后周期发送约1m以内的计算目标并取消/替换。普通启动不自动发目标，不武装。full-load包含同一个桥的compute_only模式：用真实优化里程计与EGO命令执行坐标/杆臂换算，丢弃计算结果，不创建任何PX4输出或控制使能服务；不提供虚构PX4遥测，也不声称已验证真实时钟同步/融合/控制。未测机体仅在此隔离计算模式使用canonical板上近似矩阵。

`ev`/`control`层级保留真实安装准入，当前rig会明确拒绝。控制层仍需已有显式enable接口；本模块未执行真实控制。stop遇EV/control状态不明时拒绝拆掉链路并保留监护，须按后续HW10实际验证的取消/降落流程确认落地上锁后处理；本页不提供未验证的自动降落操作。

每次运行生成fresh epoch/session，配置哈希、各进程PID/start ticks、日志保存在`artifacts/runs/<run_id>`与`.runtime/hardware-session.json`。stop只停止记录的进程组、定位和相机；保存session-exit.json，恢复原net.core.rmem_max。若报告残留，保留state先调查，不强杀无关进程。旧standalone sensors/localization会话不能与统一会话混用。

Nano日历与工作站不同，传文件后必须核对内容而非mtime。`source tools/hardware-env.bash; python3 tools/check_hardware_install.py`检查实际安装；构建后不一致时仅对受影响包force rebuild，保留旧安装备份。不得混用旧session或修改源戳以消除源龄。

2026-11-04用户取消优化定位/telemetry的0.868306s源龄硬门，`enforce_source_age=false`；原数值保留作历史测量参考，不再作为否决。未来戳、源戳倒退、接收断流、epoch、求解有效性及其它传感器门保持，源龄仍记录供任务预算分析。

## 历史实验记录：HW10 地面融合（2026-11-04；非当前状态）

用户明确跳过HW08装机复测，现场已拆桨、无遥控器；仅允许未武装EV融合准备/验证。未测rig仍保持UNMEASURED/control_usable=false，同一桥的`allow_approximate_bench_ev:=true`是本次显式近似板上EV开关，不改变真实control准入，不创建控制服务/三个控制发布者。缺遥控器时不进行武装、Offboard或接管测试。

EV-only现使用已有`/localization/imu_odom`传播状态，最多30Hz；优化解与原健康状态仍约束其有效性。高频订阅先按接收时间限频，再反序列化；输出timestamp_sample保留源采样时刻。原optimized约5Hz且延迟较大，不满足当前固件EV 200ms间隔/融合缓存规则时，不得重复发送旧姿态或改成now伪造新样本。

启动顺序必须是Agent/只读观察器/EV桥先预热，确认已初始化，再启动fresh VINS/localization；不要在健康追踪中启动大批Python进程。每次epoch更换须停止旧EV进程组，确认退出后再启动，不能复用旧桥；本轮SIGINT未结束的实例已用SIGTERM清理。

临时USB方法沿用HW07，新增`--session-label hw10 --dds-seconds 600 --unarmed-log`；备份和hook使用独立hw10路径，不覆盖hw07原备份。涉及启动钩子、SYS_USB_AUTO或物理重启时须完成前后回读和恢复。本轮已恢复SYS_USB_AUTO=2、删除hook、停止DDS/logger，原生BSON前后一致；不要在现有硬件上直接重复prepare或遗留未核对的脚本。

本轮仅得到限定静态融合证据，尚未完成方向/尺度/人工接管/必要控制退出。硬件control分支的既有优化里程计EV输出路径尚未迁移到本轮传播源方案，进入控制前需统一并验证；当前不可直接用于飞行。IMU未来戳约1.1–1.2ms触发问题也仍存在，未擅自提高门限或重写时间戳。详见HW10证据报告和CURRENT。

RViz显示的VINS姿态/轨迹已通过完整安装旋转及杆臂转换为机体参考点，和PX4均以ROS FLU（X前/Y左/Z上）显示。原始VINS光学IMU与PX4 FRD数据不改。未测安装时只读显示沿用canonical板上近似；两局部世界仍分区，不把显示偏置或姿态残差当作配准通过。

2026-11-04显示样式对照Shepherd010/UAV@7b8d33c：黑底、机体Odometry三色轴、粉色轨迹、TF与跟随机体Orbit。主显示话题/hardware_view/vins_odom仅用于RViz，twist未知，pose covariance为满足RViz有限值校验的0占位且协方差绘图禁用，不能作为导航/质量输入。原始定位接口不变。PX4分区对照在左侧默认关闭分组中选择开启，显示+3m不代表误差。参考雷达点云/控制面板未迁入；实时查看使用下述独立显示入口。

## 实时VINS特征显示

PC先启动只读显示（Humble环境），Nano随后开启新会话。RUN必须是未使用的会话ID；PC run-path与Nano一致：

```bash
# PC，先 source /opt/ros/humble/setup.bash
python3 tools/diagnostics/hardware_live_rviz.py --live --vins-only --visuals --run-path /home/jetson/D435i-VINS-EGO-ROS2-hardware/artifacts/runs/RUN
# Nano，另一终端，在硬件工作区执行
bash tools/hardware.sh start perception --run-id RUN --visuals
# PC，再开窗口
rviz2 -d config/rviz/hardware_live.rviz
```

canonical vins_hardware.json的show_track=1生成真实跟踪图。PC启动两个只读relay，--channel geometry/image，分别独立SSH；Nano统一session等待两个ready并接管各自PID。两端都按种类仅保留最新待处理帧，订阅depth=1，发送不阻塞订阅回调。

- geometry：camera_pose_visual/point_cloud最多10Hz、margin_cloud最多2Hz；imu_propagate最多20Hz。传播位姿复用完整机体转换后仅更新显示轴/TF，优化位姿仍生成粉色轨迹，不能据此宣称优化频率提高。
- image：image_track最多5Hz，640×240 JPEG quality65预览；原始1280×480跟踪图不改，JPEG预览不用于导航或特征计算。实际刷新率受算力/网络限制，不能把上限当实测速率。
- Foxy Marker按公共命名字段适配Humble，sensor/odometry使用CDR。PC核对epoch和原始world后改为隔离显示frame；world点不重复机体旋转。初始化时允许图像，几何需健康有效。历史为真实边缘化稀疏点，保留100秒，可暂为空，非稠密/回环地图。
- PC经已建立SSH连接测5次时钟偏差，最短RTT估计偏差及半RTT；status记录source_age_s、transport_age_s、remote_processing_age_s。它们测到PC处理，未包含RViz渲染/屏幕延迟；网络非对称和时钟漂移仍有误差。过旧显示帧会丢弃（body源龄0.75s、其余2s），这些仅为显示保护，不改变定位/控制健康门限。

退出PC进程后在Nano执行bash tools/hardware.sh stop，确认两个relay/传感器/定位退出并恢复rmem。此入口无PX4融合位姿，HW10尚未闭合。

## 历史状态快照：独立 TELEM1 DDS（2026-11-05）

FC USB现为独立MAVLink维护通道，TELEM1/ttyS1→CH340→Nano承载DDS；实际UXRCE_DDS_CFG101、SER_TEL1_BAUD2000000、SYS_USB_AUTO2。Nano服务microxrce-agent.service使用相同2000000速率和稳定by-id路径，源见config/hardware/microxrce-agent.service，当前配置见config/hardware/px4_telem1_dds.json。旧px4_dds.json/hw07_usb_session.py为历史USB临时方案，不直接用于这条双通道链路。

双端提速已降低主要RTT，但75秒2M窗口仍有4/65样本超过现有10ms门、同步最大间隔2.038s及姿态/位置约1s空窗；该配置是通信候选，不是EV/控制准入通过。无依据不调整timesync门、不只改一端速率，后续固定版本定位尖峰。Nano服务配置已持久保存、未做整机冷启动资格；详见progress/evidence/dds-latency-20261105-005.md。

### 历史候选：DDS-LATENCY-006 帧解析修复（2026-11-05）

当前候选已改为双端1,000,000 baud，并使用硬件专用Agent库修复异常帧后的重同步；上节2M是上一轮候选历史。源配置仍为config/hardware/px4_telem1_dds.json和microxrce-agent.service。Agent二进制仍/usr/local/bin/MicroXRCEAgent，服务单独设置LD_LIBRARY_PATH加载install-hardware-agent-framing/lib，ROS进程不继承此路径。原/usr/local库及源目录未修改。

补丁、顺序、基准和构建见dependencies/patches/agent/HARDWARE.md；固定仿真Agent默认补丁列表不变。原版断言回归失败，补丁32组断言及实际抓包重放通过；完整时效以progress/evidence/dds-latency-20261105-006.md最终窗口为准，不能仅凭修好解析器就启动EV/控制。

DDS-LATENCY-007已补齐USB恢复后的1095项完整参数复核。原生计时与完整USB帧配对将剩余延迟范围缩至转换器UART/飞控处理段；一次CH340缓冲位试验未验证有效，已恢复原1M＋6fc2修复库，无新永久钩子。现场只有CH340，下一项先审查固件调度/资源基线，不通过关闭估计器/放宽门或直接刷写绕过问题；详细局限见progress/evidence/dds-latency-20261105-007.md。

## 2026-11-05：HW10未武装EV高度基准补充

[027高度对照](../progress/evidence/hw10-ev-height-20261105-027.md)已验证本机板上EV应明确使用`EKF2_HGT_REF=3`（Vision）作为测试高度基准：用户量好10cm上移，EV约10.09cm/PX4 local约9.98cm，返回高度残差约2.5/3.5mm；一轮小幅台架结果，不是完整安装/飞行精度资格。不要再翻转ENU/NED的Z。

本轮主变量只从原GPS高度参考1改为Vision3并重启，EV_CTRL11/MAG_TYPE6沿用既有临时EV协议；baro/GPS/range及噪声/门限保留。EV已融合不代表它是高度基准。启动EV-only节点本身不会自动修改飞控高度参考；后续EV运行应明确应用经过验证的参数方案，按当前完整备份恢复，而非无条件把任何设备都写成1/0/0。HGT_REF标注reboot_required，应用与恢复都核验未武装、保存/重启/回读。TELEM1 DDS/原Agent与023固件/024桥接器保持。

实际测试维护/恢复脚本与完整原始记录在`artifacts/runs/hw10-ev-height-20261105-027`，只作本次复现证据，不直接覆盖同run目录重复运行（标记/ready文件须属于新session）。027结束已恢复本机原HGT_REF1/EV_CTRL0/MAG_TYPE0、重启和1095项核验，当前没有永久启用Vision参考；后续参数采用与其余动态出口一起冻结。
