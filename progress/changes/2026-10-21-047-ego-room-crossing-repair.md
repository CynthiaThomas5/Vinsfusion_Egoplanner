# 房间穿越修复与起飞诊断（进行中）

对应[对话](../../collaboration/dialogues/2026-10-21-047-ego-room-crossing-repair.md)、[证据](../evidence/ego-room-crossing-repair-20261021-01.json)。

源码／配置：新增 `tools/run_gpu_viewer.sh`，设置NVIDIA PRIME/GLX后启动RViz或Gazebo；`run_gpu_vio_sitl_runtime.sh` 服务器显式增加 `--headless-rendering`；说明更新到config与docker README。新增单变量诊断 `vio_climb_probe.json`（最大上升0.5m/s），只用于run-local airframe叠加，不改变默认staging。`0009-lm-trust-region-experiment.patch` 保存隔离求解器候选，基准固定VINS提交+canonical0001–0005，不依赖0006–0008；canonical vendor与sources.json未改。

GPU证据：同一显示默认GLX为Mesa llvmpipe，PRIME/GLX offload为RTX3060。旧服务器进程同时有Mesa GLX路径，单独EGL探针不能代替真实服务器渲染证明；repair02 Ogre日志确认NVIDIA实际renderer。RTF由约0.25提升到0.626，优化odom最大回调间隔降至0.119s。

修复后基线：repair02原材质仍在source16.504s出现accel_bias_norm0.151129，36输入特征、34双目／长轨，solver usable，保持原0.15门后锁定。

视觉单变量：repair03只改run-local表面材质，程序断言collision XML哈希不变，固定随机灰度纹理真实被相机看到；原 `simulation/worlds/ego.sdf` 未修改。输入特征约141，40墙钟秒窗口连续稳定37.65s、偏置最大0.00660、RTF0.597，原健康门通过。该结果不足以宣称运动稳定或纹理是唯一根因。

真实起飞：repair03经桥服务使能、Offboard/ARM/TAKEOFF，PX4记录Takeoff detected；起飞过程中accel_bias_norm_exceeded，未到ACTIVE，自动LANDING→LANDED且上锁。repair04相同纹理和GPU，仅用配置将MPC_Z_VEL_MAX_UP改0.5m/s；静置40秒通过，实际起飞中normalized_cost_exceeded，自动落地上锁。两轮都没有发导航目标，更没有穿越或完成10秒稳定悬停。

关键样本：repair04 source52.472s，9次迭代但initial_cost==final_cost==5773.894879、residual_components4105，normalized_cost1.67723；bias0.007367、180特征／162双目／134长轨，solver usable。前后代价分别379.736／481.838，说明该次求解无代价下降，不能直接归因残差组；未采Ceres分组。

当前候选：只把DOGLEG改为LEVENBERG_MARQUARDT，迭代／时间／健康限制不变。复制源码到ignored artifacts隔离构建，无同名包进入主src。首个构建容器退出255、OOMKilled=false，原因未定；独立单编译任务恢复构建。配置目录已补齐为完整安装输入。候选运行结果待更新，不升级阶段。

验证：默认与offload真实GLX查询、服务器Ogre日志、静态／起飞SITL报告及落地状态已保存；运行bash/Python语法检查、结构与diff检查通过。无ROS包源码变化，新增候选须单独编译及运行后才能评价。纹理和上升参数均为实验，未计正式验收。

后续进展：LM候选单任务隔离构建通过（1包、2分53秒，另有上轮未完成构建痕迹复用）；SHA及二进制路径已写provenance。候选相比#181运行基线还去掉了两处计时诊断源码差异，因此不是与#181严格单变量binary A/B，不能独立证明策略因果性。repair05实际进入ACTIVE，10仿真秒悬停无质量中止，主动降落后仍accel_bias_norm_exceeded，最终落地上锁。脚本hover PASS不能扩大为全程质量通过。

为覆盖从x=-8初始化到对侧的16 m相对目标，默认 `ego_planner.json` 地图改40×40×6 m，膨胀改更保守0.5 m，仍PROVISIONAL；新增 `room_crossing_goal.json`。配置传递7测试通过。repair06从启动manifest确认实际40m／0.5参数与LM二进制prefix。实际起飞进入ACTIVE，16m目标被接受、1条样条／114条READY；随后pose_stale、桥external_odometry_stale中止并降落上锁，后续normalized_cost越限。规划日志约0.45ms，不能把位姿间隔直接归因规划耗时。

接管缺陷：repair06目标yaw=-0.001062，首条轨迹yaw=-0.769565。实际样条控制点前三项约[-0.91527,-0.91413,-0.07643]，三次B样条起始值约-0.774。`fillTaskMetadata` 用起始微小位移方向覆盖里程计yaw，产生约44度跳变。独立数学回放验证前三个控制点种入当前航向后初值／零角速率成立。0035候选只修这个边界，供应源仍未修改；短样条终端yaw和动态重规划导数不作通过结论，实际首指令验证待repair07。

构建版本复核：0035首次CMake构建虽然通过，却解析到P0旧plan_env／traj_utils等依赖，因此排除作候选验证，正在显式指定#297 canonical依赖重建。反查repair06实际可执行文件和已加载共享库，均确认来自#297（VINS来自LM候选）；不能把repair06接管失败归因旧运行版本。repair07改用按顺序local_setup加载并记录实际包prefix，避免候选构建或运行时父链覆盖。

0035按#297依赖的隔离重建已通过。repair07运行时prefix指向LM VINS及yaw候选。用户要求打开窗口：发现原Xauthority路径已失效，使用当前桌面授权重新打开两个viewer；Gazebo房间和RViz相机／Inflated Occupancy Map截图核对通过。当前07未使能或发送目标，首命令及穿越仍待验证。显示凭据仅在容器临时文件，不进入项目记录。
