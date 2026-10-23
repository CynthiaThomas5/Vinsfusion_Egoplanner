# loop_fusion 单会话观察接入

[任务约定](../../collaboration/dialogues/2026-10-22-058-loop-observer.md)。

## 实施前的范围和出口

- 沿用 zinuok/VINS-Fusion-ROS2 `72023bc5d2abb14faa4c02a5c040d84f996b587a` 的 loop_fusion（GPL-3.0），不引入第二份估计器。补丁为 dependencies/patches/vins/0015-loop-observer-transport.patch，应用在 0014 之后；新增 package_roots 和 BRIEF 资源哈希。
- 原输入：mono8 左图、同源 keyframe_pose／keyframe_point、原始 VINS odometry、extrinsic。以不可变 session 绑定 namespace／标定哈希；同一个模型／标定生成文件，不手写另一份外参。
- 输出在 `/loop_observer/s_<epoch>`、`loop_<epoch>_map`；不反馈原估计器，不连接 `/localization`、EGO 或 PX4，不发布 map→odom TF。
- 上游 transport 存在2000深度订阅、无界队列、图像断流隐式new_sequence、非受控工作线程退出和数据竞争。用有界单线程ROS传输包装，保留上游 KeyFrame／DBoW／PnP／4DoF 优化算法；优化线程与回调共享互斥、可停止并join。
- 关键帧与相机曝光配对最多容许2ns的浮点header序列化差异，不匹配下一帧、不改源戳。前10个成功配对保留上游warmup，之后按0.2m平移采样；最多1000关键帧、每路64缓存。资源上限报错，不静默修复地图。
- 实验：新epoch当前room／现有16m任务，额外启动可观察后端和只读记录。预期关键帧、当前稀疏特征及位姿图持续输出，帧一致，输入身份明确，原控制链仍成功落地。此路线不保证回访；没有经过几何验证的回环就明确报告0，不宣称漂移改善。

## 进行中的验证

- 第一次构建失败：新传输包装遗漏显式 Odometry C++ header；补齐.hpp后17包构建通过。
- 标记线段四元数显式设为单位值，避免可视化零四元数；最终构建17包通过。
- 入口5项新单元及runtime binary哈希检测通过；服务器154项回归＋真实action集成通过。
- 合成传输探针在ROS_DOMAIN_ID=185运行，与项目84隔离。初次因探针Python把Quaternion.w赋整数1触发ROS转换断言，修正为1.0；失败日志保留，实际探针／SITL结果待补。

## 修改文件与完成结果

- `dependencies/sources.json`、`dependencies/patches/vins/0015-loop-observer-transport.patch`／README：同一上游新增loop_fusion和support_files；词袋／模式SHA256固定，GPL来源保留。实际数值算法文件不复制到第二个运行包。
- `config/components/localization/loop_observer.json`：observation_only，64缓存／1000关键帧／0.2m采样。`config/rviz/loop_observer.rviz`、`tools/prepare_mapping_rviz.py --loop`：单独map frame显示当前特征、图路径和边，不把odom占据地图当作全局修正后的地图。
- `tools/run_loop_observer.py`、`tools/loop_runtime.sh`、`tools/project.sh loop`：核验session、源设置、安装资源与binary，绑定独立namespace，原子拒绝同epoch重启，保留PID／实际退出码；不改变默认启动行为或控制链。
- `tools/runtime_manifest.py`：纳入实际安装loop_fusion_node哈希；`test_runtime_manifest.py`验证改动可被发现。
- `tools/diagnostics/record_loop.py`：旁路只读采集状态、路径／边、当前特征、修正位姿与进程资源。`tools/check_loop_observation.py`：15项真实记录检查，可绘图；没有回环时检查修正位置与raw完全一致。
- `tools/probe_loop_transport.py`：真实二进制、独立ROS域合成传输／退出测试，不冒充SITL。`tools/test_loop_observer.py`6项、`tools/test_loop_observation_check.py`2项：配置、不可变资源、控制／frame／退出拒绝及JSON数值序列化。docs/running、CURRENT和本轮证据更新，milestones阶段不变。

## 诊断、失败与修正

1. 新transport最初缺Odometry C++ header，构建失败；补齐.hpp，17包实际构建通过。可视化顺序／回环线段显式单位四元数。
2. 合成探针首次Quaternion.w为整数导致ROS Python转换断言，修正为浮点1.0。随后发现错误退出超过8s，显式使用可提前释放的图对象、停止／join线程，并在rclcpp静态资源销毁前释放ROS对象；最终探针错误退出2、SIGINT退出0。一次探针与重建时间重叠，排除该结果；最终探针记录binary SHA256并与最终SITL一致。
3. SITL 01：导航9项通过，但后端一直等待extrinsic，图节点0。定位到当前上游 `pubTF()` 提前return；固定外参直接读取同一session文件，要求estimate_extrinsic=0，若消息出现则检查一致性。未启用损坏的TF段，也没有另写外参。先等飞行落地，再停止观察器、构建并新开epoch。
4. SITL 02：起飞前telemetry_stale，独立遥测订阅观察到最大约0.369s接收空窗，最大源间隔约0.164s。bridge保持DISABLED／armed=false／landed=true，未发enable或导航目标。没有清锁／放宽门，保留全部失败数据，正常结束该会话。
5. 03将记录器与新栈同时启动，导航9项及图观察均成功：65节点、250顺序边、最多122特征、回环0。不能据此声称启动空窗根因已修复。
6. 完整fetch暴露0015基准应包含既有0003的cv_bridge头文件修改；更正补丁基准（数值源码／已编译文件字节不变），再完整fetch，222文件与canonical vendor逐字节一致，28个核心算法文件与原上游一致。初次fetch失败日志与运行中的旧清单快照保留。没有在飞行中修改清单。
7. 最终清单另开04冷启动：导航9项与后端15项检查全部通过，67节点／258顺序边，回环0／优化0；后端SIGINT退出0，确认落地上锁后停止容器，exit0。最终运行合同`9d14860aa693d92bcacdcbed364aecc9e3adfcadfed2573dc8df2375b973481f`。
8. 离线报告最初遇NumPy bool_不能JSON序列化，统一转换为bool并补负例／序列化测试；真实记录复算及图形生成通过。图形来自实际ROS输出，没有伪造地标、轨迹或成功消息。

## 验证与边界

- `bash tools/project.sh build ros`：最终17包通过；日志build-05。最终补丁基准修正重建出完全相同源码，不触发无意义的算法重新构建；04使用最终清单验证。
- `bash tools/project.sh test`：最终157项＋真实action／250Hz时钟集成通过，最大pose接收龄0.054s。
- `python3 tools/fetch_dependencies.py --source vins_fusion --target artifacts/runs/loop-backend-20261022-058-fetch-check`：完整固定上游／补丁重建通过，222文件一致；运行输入与安装节点哈希见manifest。
- ROS_DOMAIN_ID=185探针最终通过；domain84的01–04现场证据与其分开。
- `python3 tools/check_loop_observation.py artifacts/runs/loop-observer-20261022-058-04 --plot`：15项通过，图形已检查。RViz预设生成／YAML通过，本轮未验证实际GUI渲染。
- 最终运行图显示仅原始相机／VINS输入，独立loop输出，无真值订阅、控制或TF发布。对比#057，已有运行源／配置／binary全部相同，仅新增loop配置／预设／binary与依赖清单变化。
- 原始ULog保留服务器并记录哈希，其余消息／报告／失败日志已回收；当前无运行会话。Nano、桌面和真实设备配置未改，未提交／推送。

本次仅完成后端观察接入。无实际回环／优化、无地图复用或全局地标重建、无map→odom控制接入、无5分钟或实机保证；初始化前十个配对仍是上游warmup。下一小点建议短往返回访验证，等待用户推进。[报告与全部证据](../evidence/loop-observer-20261022-058.md)。
