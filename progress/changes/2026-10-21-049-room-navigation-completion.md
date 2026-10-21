# 持续房间导航修复（进行中）

对应[对话摘要](../../collaboration/dialogues/2026-10-21-049-room-navigation-completion.md)。用户要求持续修复至房间另一端指定目标到达，不以部分位移收尾。

源码：桥在已通过地面未解锁使能检查后重新捕获当前对齐，随后固定；已锁定bridge/alignment故障拒绝使能；若重新采集失败则撤回预发送并拒绝。保持所有健康门限、坐标约定、唯一控制发布者。实际timer／enable回归共2项多子场景通过，原supervisor11项通过；uav_px4_bridge独立colcon构建通过1包1.71秒，产物`artifacts/runs/ego-bridge-alignment-fix-20261021-01/install`。

repair08：40秒前检通过；使能前propagated_from_future锁定，原始记录source 34.335999999、clock34.308，超前28ms超过原20ms门。无使能、无解锁。门限未改，原始未来观察保留。

repair09：前检通过并起飞；对齐yaw误差从初期约0.039rad收敛至ACTIVE约0.00087rad，未再先触发alignment故障。前进约0.84m后EGO同步在source54.520秒停止，now55.028与last_occ54.624之差超过原0.4s门，进入EMERGENCY_STOP并保持。上游optimized最大接收间隔0.152秒，独立转发pose持续；仍需区分EGO接收与同步路径。通过action取消和桥disable结束该轮，PX4落地上锁且桥LANDED，故障降落终态修复获得本轮支持；降落阶段后续偏置锁定，非全程定位通过。只读debug_truth评估记录从x=-8到约-7.154，最后地面，未输入定位／规划／控制。

传输候选：`config/middleware/fastdds_local_shm.xml`显式本地UDP与32MiB SHM、2048描述符队列；不改QoS、sysctl或健康门限。仅repair10显式启用，尚未成为默认launch配置。主机rmem_max=212992，sudo不可用，未修改系统。参考[Fast DDS 2.14共享内存文档](https://fast-dds.docs.eprosima.com/en/2.x/fastdds/transport/shared_memory/shared_memory.html)；当前Fast DDS2.14.6／rmw_fastrtps_cpp8.4.4。XML解析通过，实际进程映射另存transport-runtime.json；有效性待运行结果。

所有轮次使用不同domain／partition／epoch。真实执行结果、限制和下一步继续追加；未升级阶段。

repair10：显式SHM映射有效（每段约35.1MB含管理开销）；ego_camera_pose／depth独立回执最大间隔分别0.159／0.153墙钟秒、源戳最大间隔0.036s，无Depth Lost。实际推进至VINS[13.661,-0.045,0.903]，Gazebo真值最终落地x约5.86，尚未到x=8。之后首因external_odometry_stale，随后telemetry_stale锁定及pose_stale动作中止；最终LANDED上锁。失效窗原始遥测两帧墙钟回执间隔0.6555s，Ceres求解仅约0.028s且normalized cost约0.68，不能归因求解变慢。日志显示solver结束到输出后处理间有延迟，精确阻塞位置待确认。

repair11隔离启用`RMW_FASTRTPS_PUBLICATION_MODE=ASYNCHRONOUS`，其余与repair10相同；验证发布发送是否阻塞估计线程。参考[Fast DDS 2.14 ROS 2配置](https://fast-dds.docs.eprosima.com/en/2.x/fastdds/ros2/ros2_configure.html)。没有改VINS数学或保护门限，不把一次运行差异作为严格因果结论。

repair11异步发送未改善：起飞阶段external_odometry_stale，随后alignment漂移锁定，未ACTIVE／发目标；最后桥LANDED且armed=false/landed=true，定位仍TRACKING。不是成功对照，下一轮恢复同步发送。

OpenCV本机默认16个线程（4.6.0，TBB），环境OPENCV_FOR_THREADS_NUM=1未改变getNumThreads结果。隔离0010补丁在VINS main调用cv::setNumThreads(1)，保留LM数学和健康门限；新候选`ego-vins-opencv1-candidate-20261021-01`。首次缺camera_models配置失败；P0依赖构建中断并排除，最终显式指定与LM相同的#181 camera_models，构建待结果。

离线评估脚本`repair12/evaluate-crossing.py`对repair10读取Gazebo真值轨迹、SDF柱／墙碰撞几何和#246的IMU名义球包络；简单box/cylinder距离断言通过。最近目标XY约1.98m，确认未到达；采样的非地面障碍包络余量约0.334m，仅单轮离散诊断，非连续碰撞验收。核对[Gazebo OdometryPublisher源码](https://raw.githubusercontent.com/gazebosim/gz-sim/gz-sim8/src/systems/odometry_publisher/OdometryPublisher.cc)发现robot_base_frame只是标签，默认数据来自模型worldPose；评估因此按模型原点解读并旋转平移[0.12,0,0.08]重建IMU，不依赖误导性child-frame标签。未修改在线真值输出，也不重写历史证据。

0010候选完整构建通过1包5分30秒（KITTI预存fscanf警告）。repair12日志确认OpenCV=1；运动时optimized最大回执间隔0.391秒，external_odometry_stale后normalized_cost锁定；未ACTIVE、未发目标，最后LANDED上锁。单线程未改善运动时效，不据此认定所有延迟来自线程数。

0011为0010的替代补丁，main支持经过整数范围校验的VINS_OPENCV_THREADS；不指定时沿用OpenCV默认，仅实验启动显式从`config/components/localization/vins_runtime.json`读取4。新wrapper按原CMake生成flags/link命令编译，并复用0010已构建且数学未变的libvins_lib.a和同#181 camera_models；命令、库／补丁／二进制哈希在`ego-vins-thread-candidate-20261021-01`，没有修改既有候选二进制。6项参数自检通过（5非法值返回2，合法4由实际getNumThreads记录4后无配置usage返回1）。

repair13另减少验证脚本观测负载：去掉raw/ego图像重复反序列化，到ACTIVE后退出只读occupancy订阅；本体定位／建图／导航健康门、轨迹和PX4唯一控制均不变。这是线程与观测负载联合候选，不能与repair12作严格单变量因果对照。独立紧凑姿态、轨迹、状态与Gazebo debug_truth评估记录保留。

repair13：实际OpenCV=4且降低观测负载，起飞阶段仍external_odometry_stale，后alignment及normalized_cost锁定；未ACTIVE／发目标，最终LANDED上锁。不能继续以线程多作为已证根因。恢复vins_runtime.json至本机实测默认16（仍实验显式值）。repair14增加仅vins_node有效的LD_PRELOAD慢pthread_mutex_lock／rcl_publish计时（>50ms记录，其他进程透传）；合成120ms锁等待自检通过。它是观测工具，未绕过任何健康门。

GPU复核：当前RTX3060 GPU利用率采样38%、显存1630MiB，Gazebo Ogre实际GL_RENDERER为NVIDIA3060。VINS use_gpu/use_gpu_acc_flow/use_gpu_ceres均0；OpenCV4.6 CUDA device_count=0且无CUDA构建字段，Ceres配置为CERES_NO_CUDA；当前host/container均未找到nvcc。CUDA光流／角点源码被GPU_MODE编译宏保护，现CMake未启用；不能只改运行开关，尤其会跳过未编入的CPU分支。仅记录可迁移方向，未安装CUDA／重建GPU算法。

repair14诊断部署失误：LD_PRELOAD虽在函数内按exe筛选日志，但仍对Python进程劫持rcl_publish，RTLD_LOCAL加载路径无法正确解析透传目标，导致5个Python节点exit -11。前检缺定位／控制状态失败，无使能／解锁，完全排除运行结论。已修为独立VINS可执行wrapper加载，其他节点不继承LD_PRELOAD；探针同时过滤executor常规等待日志，仅记录VINS调用端慢mutex和慢publish。缩小范围后合成锁自检重跑，repair15使用原二进制、默认16线程、相同门限重新验证；未将失败诊断归因GPU／算法。
