# Nano D435i PX4 实机迁移执行方案

具体实施请使用[Agent模块任务书](hardware-agent-workbook.md)：HW01–HW14逐项定义代码入口、依赖、动作、最小验证和完成条件。本方案保留路线选择与调查依据。

日期：2026-11-02。源码基线：`dbb724f`，分支 `quad250-follow-2026-10-31`，开始时工作树干净。

本轮范围是代码审阅、SSH 只读调查和迁移规划。实机安装、参数写入、武装与飞行未执行。历史仿真 GOAL 和通过记录保留；本方案作为新实机工作的执行入口，替代旧路线中尚未针对本机核实的环境假设与工作顺序。

## 采用的路径

**先保留 Nano 的 Ubuntu 20.04／Foxy 和已经排过错的相机驱动，在独立实机工作区移植本仓库固定版本；依次完成手持定位建图、拆桨 EV 融合、悬停、短目标、避障。** 不先刷系统，不新增一份 VINS/EGO 算法，不把飞行核心放到 Wi-Fi 对端。PC 只负责构建辅助、RViz 和分析；Nano 运行相机、VINS、地图、EGO、导航、bridge 和 DDS Agent，PX4 保留自身控制内环。

这是根据现有 ARM/Foxy 驱动和同一 VINS 基准已有运行记录作出的工程选择，尚未证明当前仓库全部补丁可在 Foxy 构建。先做一次有界构建适配；若问题只是 Python/ROS API 与头文件差异就直接修复。若变成依赖大规模降级或算法改写，则停止该路径，改评估 ARM64 Jazzy CPU 容器。容器需要单独证明旧内核上的启动、USB/IMU和资源表现，不能直接导入当前 amd64 镜像。两条路径不同时实施。

若完整负载在 Nano 上持续积压，先关闭 RGB、显示和非必要记录，缩小局部地图与限定任务空间，再按诊断调整线程、图像负载；每次只改一个主要变量。两次有针对性的调整仍无改善时，报告测得的性能缺口，讨论更换计算平台。不会通过抬高过期门限掩盖算力不足，也不预先要求购买硬件。

Jazzy 官方发布支持 Ubuntu 24.04 的 amd64/arm64，并不等于本机 20.04 可以直接安装同一环境，见 [ROS 官方发布说明](https://www.openrobotics.org/blog/2024/5/ros-jazzy-jalisco-released)。

## 已核实的基础

| 项目 | 结果及用途 |
| --- | --- |
| Nano | 原版 4GB，aarch64，内核 4.9.337-tegra，L4T 32.7.6，Ubuntu 20.04.6，ROS Foxy；调查时可用内存约 2.5GiB、磁盘约 71GiB，均为空闲快照 |
| D435i | 当前序列号 `243622073269`，固件 `05.17.03.10`，USB3 5000M，Video/HID 已枚举；枚举不等于各数据流通过 |
| PX4 | `/dev/serial/by-id/usb-3D_Robotics_PX4_FMU_v5.x_0-if00` 指向 ttyACM0；仅确认 USB 标识，具体板型、固件版本、参数、DDS 模块和串口用途待读回 |
| 原有相机基础 | `~/realsense_debug` 有 SDK 2.58.1 HID-hold/sensitivity、Foxy wrapper 和双目/IMU脚本；系统默认 rs 工具/旧源目录还存在 2.50.0，部署须锁实际加载库，不能凭目录名认定运行版本 |
| 双目/IMU历史记录 | `ros_stereo_rgbd_imu_20261015_30s.json` 记录 640×480、双目/深度约14.9Hz、IMU约196.8Hz，单调性检查通过，深度16UC1；属于历史短时输入证据 |
| 原有 VINS | `~/realsense_debug/vins_integration/environment_manifest.json` 记录同一基准 `72023bc...`、Ceres2.1/OpenCV4.2、600秒静态资源和启动覆盖回归；动态精度、当前仓库全套补丁与飞行未通过 |
| 候选标定 | `vins_integration/config` 针对当前序列号；清单仍是 PROVISIONAL，时间偏移候选约−9.338ms，IMU坐标为 optical，不能当最终安装标定 |

旧 `environment_manifest.json` 对应另一台相机 `035422071615`，其标定和通过记录不得套用。原有 checked adapter 明确只输出实验接口、无算法健康保证；不能直接接飞控。历史30秒记录右红外 frame 名与左红外相同，需要核实驱动约定和 CameraInfo，而非直接改名“修复”。

以上来自只读命令与已有报告，未在本轮启动相机数据流或访问飞控控制接口。已有目录均保留只读；迁入时记录原路径、commit、diff、SHA256、许可和适用范围。

## 必须适配的代码边界

| 边界 | 当前代码事实 | 实机最小改动 |
| --- | --- | --- |
| 构建环境 | `docker/Dockerfile.vins` 固定 amd64 仿真基础；Python有 `removeprefix` 和 `_rclpy_pybind11` 导入 | 新建独立 ARM/Foxy 构建入口，先构建接口、VINS/EGO与必要 own 包；修实际遇到的 API、头文件和依赖兼容，不构建 Gazebo/PX4 SITL；第三方兼容修复另存补丁 |
| 标定来源 | `tools/generate_vins_config.py`、localization/node.py、mapping/adapter.py、vio_ego_bringup.py 都读取 SDF | 增加一个真实 rig 配置来源；VINS、输入校验、深度投影与安装变换共用它；仿真仍用原 SDF；同样保存不可变 session/epoch 与配置哈希 |
| 陀螺偏置 | `vins_sim.json` 开启 `known_zero_gyro_bias=1` | 实机明确置0，恢复正常偏置估计；不照搬仿真噪声参数，也不把旧 IMU sensitivity 修正未经确认再叠加一次 |
| 相机输入 | 固定 `/sensors/d435i/*`，实机现有 `/camera_b/*` | remap 到既有契约；保留真实 frame、stamp、CameraInfo；只在确有格式/坐标差异时适配，不另写相机驱动 |
| 深度 | mapping_input.py要求32FC1，历史实机输出16UC1 | 按冻结驱动的ROS输出单位转换为米，保留0等无效值语义和源stamp；核实SDK depth_scale与wrapper是否已归一化，禁止重复缩放；原生深度配原生内参，首版不对齐RGB |
| 坐标 | vision_odometry.py按源body为FLU转换FRD，旧实机VINS body是IMU optical；bridge从SDF取杆臂 | 使用完整IMU optical→机体FLU→PX4 FRD旋转和平移，统一位置、四元数、线/角速度；确定机体参考点及杆臂唯一补偿责任，不能只换frame_id或yaw |
| 时钟 | localization订阅/clock；bridge构造时只接受gazebo_lockstep；launch写死use_sim_time=True | 实机统一use_sim_time=False；localization从系统ROS时间计算源龄、steady clock计算接收龄；bridge新增系统时间/uXRCE同步路径，保留真实timestamp_sample，不发布假/clock冒充SITL |
| DDS消息 | 当前/fmu/out/*含版本后缀，与仓库PX4 v1.17配套 | 先读固件与DDS输出清单，再锁px4_msgs、Agent和真实topic；不能从FMUv5 USB名推断固件兼容。优先沿用兼容的既有固件，不为对齐仿真立即刷机 |
| 质量/失效 | health.json与depth_gate.json明确质量/时效大多仅观察 | 首飞只补必要的定位断流/旧设定点拒绝与退出，并保留epoch取消清图；先地面验证，不扩成六类故障专项或重做仿真全矩阵 |
| 启动 | 现有入口绑定Gazebo桥、SITL与仿真默认任务 | 新增明确的hardware启动入口，分sensors、perception、EV-only、control；默认未武装，EV-only不发布模式/设定点；唯一控制发布者继续是uav_px4_bridge |

真实安装标定至少包含左右内参/畸变/基线、相机IMU外参、深度外参、IMU到机体安装、机体含桨包络、固定分辨率、时差及来源。先审查并验证现有候选；只重做有明确问题的标定项。注意旧候选left/right图像的矫正状态，不能将已矫正图像和原始畸变模型混用。

上游 [VINS D435i 配置](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/master/config/realsense_d435i/realsense_stereo_imu_config.yaml)可参考结构，数值不代替本机标定。[RealSense 官方驱动说明](https://github.com/realsenseai/realsense-ros)解释IMU插值到gyro时间；它不自动消除图像/IMU时差，实际参数类型仍按现有锁定wrapper处理。

## 按可交付结果推进

以下为新的实机子项，不继承仿真N目标的通过状态。每项达到核心出口后直接进入依赖已满足的下一项；需要实际搬动设备、拆桨或现场飞行时，再取得对应现实条件。普通“继续”按仓库单项预算执行；用户明确授权完成某实机目标时持续推进其完整范围。

| 顺序 | 产物和动作 | 最小验证与完成条件 |
| --- | --- | --- |
| H0.1 环境与传感器入口 | 独立实机工作区、依赖清单、现有驱动/候选标定的来源哈希、话题和单位适配 | 实际 ARM 构建通过；一次约60秒左右图像+IMU+深度实采样，确认频率、配对、时间域、单位和无效深度。只修明确问题，不重装已有可用SDK |
| H0.2 手持VINS与建图 | 当前仓库补丁运行、真实session/rig、关闭零偏先验；用量测墙/箱做地图 | 一次2–3分钟静止→三轴平移→慢yaw→返回；独立量测位移/回到起点误差，核对重力与轴向、墙的位置/尺度。人工动作由现场人员完成；无参照不能宣称全程绝对精度 |
| H0.3 Nano完整负载 | VINS+地图+EGO+导航+bridge离线计算，关闭真实控制 | 按首批任务时长做一次5–10分钟地面满载；报告图像/优化/规划实际频率、源龄P95/P99/最大空窗、CPU/RSS/温度、队列趋势。主要判据是无持续积压、满足所选低速任务时效；不以CPU低于某任意百分比判合格 |
| H1.1 拆桨EV联调 | 备份真实参数/固件信息，锁DDS与px4_msgs，落实完整安装变换和真实时间 | 手动前/左/上和yaw，PX4回读方向及幅度正确；ULog证实EV实际融合、局部状态有效和无持续创新拒绝；此时bridge只发EV，不武装、不切Offboard |
| H1.2 拆桨控制联调 | 唯一bridge控制、明确人工模式接管/Offboard-loss、与实机同步的少量参数差异 | 检查20Hz心跳/设定点、新鲜度、取消与epoch清图；地面停VINS或断开Agent各一次验证必要退出。无需真实空中故障注入，遥控接管必须现场可用 |
| H2 首次悬停 | 人工确认基础机体可正常飞行，再进入视觉/Offboard保持 | 宽敞空场、有人接管，候选高度0.5–1m，先一次约30秒保持→正常降落上锁。稳定后补必要重复，不先做导航；高度按视野、场地和机体定 |
| H3 短目标 | 同一配置执行约1m前向目标→停止→正常降落 | 候选速度0.15–0.2m/s，实测实际位移、到达和停止；成功后才加yaw/升降与返程。候选值待H0/H1实测确认，不直接复制16m仿真任务 |
| H4 避障 | 大净空单障碍，再两个错位障碍 | 直连确实受阻，真实深度占据更新、EGO绕行、实际到达且无碰撞；机体尺寸/跟踪误差决定膨胀，仿真0.299m不直接视作真实安全距离；限制侧后方盲区运动 |
| H5 使用范围交付 | 统一硬件入口、配置、日志与已测限制 | 能重复执行上述核心流程；记录速度、场地、照明/纹理、障碍材质、任务时长和人工接管条件。回环、语义、探索、动态障碍与长时优化不阻塞本次迁移 |

H0.2动态误差、H0.3实际源龄及H1融合结果形成首飞的具体预算：定位/跟踪误差和制动距离必须能被试验场净空容纳。不能现在凭仿真数字承诺厘米精度，也不把完整动捕设施作为地面初步联调前置。

## PX4联调的具体选择

1. 先备份并读回版本、空气机架/传感器状态、串口配置及DDS模块；USB ttyACM0枚举通常只说明存在串口，不代表已是XRCE链路。选择当前固件支持的USB串口或TELEM UART运行DDS，Agent独占对应设备；GCS不争用同一串口。UART电平/端口/波特率按实板说明配置。
2. 消息定义与飞控固件对应。若最终采用仓库v1.17，核对具体FMUv5板目标是否包含DDS与所需输出；Agent按官方v1.17对应版本锁定，不拉latest。[PX4 DDS官方说明](https://docs.px4.io/v1.17/en/middleware/uxrce_dds)提供Agent v2.4.3及ROS版本适配、串口配置和同步选项。
3. 实机默认考虑启用 `UXRCE_DDS_SYNCT`，以实测确认同步稳定。ROS系统域的采样戳交给DDS转换，不再叠加SITL lockstep的反偏移逻辑；`timestamp`是发送时间，`timestamp_sample`保留采样时间。以实际固件序列化路径为准，防止双重校时。
4. 只调整EV融合、参考点、延迟/噪声和Offboard相关必需项，按版本核对 `EKF2_EV_CTRL`、`EKF2_EV_DELAY`、`EKF2_EV_POS_*`、`COM_OF_LOSS_T`、`COM_OBL_RC_ACT`。不导入SITL机架/预检豁免，不在桥和EKF同时补偿杆臂。[PX4外部定位文档](https://docs.px4.io/v1.17/en/ros/external_position_estimation)说明EV融合与安装/延迟配置。

## 验证投入与记录约定

遵守用户七项要求：达到可实施认知就执行；验证只覆盖改动和真实风险；问题修根因后只复验受影响部分；相同环境不重复检查；首版核心链路可执行即交付；常规可逆选择自主推进；不增加假设性防御框架。

实机新增时间/单位/坐标逻辑各保留少量有物理意义的定向检查；对应包实际构建、核心地面实采样与PX4融合读回不能用结构检查代替。不会要求重跑751个仿真单测、旧三场景资格或完整故障矩阵来放行一个相机remap。

每次记录源码/标定/参数版本、实际命令、关键结果和未解项。轻量证据放progress/evidence，大日志放artifacts/runs；原始图像只做必要短包，避免microSD持续写入影响控制。远端参考只作读取，不回馈在线定位。Wi-Fi只用于观察与下发目标，控制闭环留在机载。

开始H1前需要现场补齐机体含桨尺寸、相机固定安装姿态/位移、PX4具体板型和基础飞行情况；开始H2需要确认拆装桨流程、遥控模式接管、供电和实际场地。它们不阻塞先完成H0.1的软件工作。

**唯一下一项：H0.1，独立ARM/Foxy构建与真实传感器入口。** 本轮规划交付完成不等于H0/H1或实机飞行通过。
