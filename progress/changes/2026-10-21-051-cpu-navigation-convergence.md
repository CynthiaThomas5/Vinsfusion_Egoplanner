# CPU导航收敛：几何误匹配候选（进行中）

对应[对话摘要](../../collaboration/dialogues/2026-10-21-051-cpu-navigation-convergence.md)。用户确定使用CPU定位／规划，以稳定到达为收敛。采用连续3次同版冷启动完整飞行检查，原阶段门槛保留。

repair15结果：实际ACTIVE并接受16m目标，最终估计[2.206,0.675,0.936]m；首个锁定是normalized_cost_exceeded约1.0277，不是锁等待。optimized最大回执间隔0.152s，慢锁／发布探针无>50ms记录。原始首次越线stamp57.820：visual cost1958.760、marginalization114.303、IMU4.527、总2077.589，视觉占94.28%；177特征、155双目、110长轨、bias0.0574、solver usable、求解0.0315s。之前finalcost552.949，说明视觉项突增；随后动作中止并LANDED上锁。这一窗不能据此排除别轮曾出现的消息时效问题。

0012隔离补丁恢复已有rejectWithF调用（原调用被注释），使用现有F_threshold=1。旧实现会reduce尚未按光流筛减的cur_un_pts，存在status长度错位越界风险；删去该多余筛减，因为normalized points在补点后统一重算。RANSAC返回mask长度不符时保持原匹配，交给原健康门裁决。

只在ignored artifacts复制完整候选源码；复用LM数学估计库、同#181 camera_models及0011主程序，按原CMake flags编译新tracker对象并替换独立archive对应成员后链接。未修改canonical vendor或sources.json。哈希、命令、构建结果在`artifacts/runs/ego-vins-ransac-candidate-20261021-01`。

真实候选C++函数测试通过：80个干净匹配全部保留，16误匹配剩1；静止81点保留；少于8点7点保留；刻意保留200项旧normalized数组，函数不再越界筛减。使用-UNDEBUG确保assert有效。CPU及健康参数不变，SITL运行repair16待结果。算法改变可能影响退化／低视差情况，合成测试不能替代飞行与独立复测。

repair16：前检连续38.86s、RTF0.620通过；实际导航至估计[15.193,0.040,0.859]m，距目标约0.779m，随后normalized_cost≈1.041锁定、动作中止并LANDED。optimized最大回执间隔0.175s。首次越线source97.716：91特征／68双目／55长轨，bias0.0164、solver usable；cost1377.860（visual978.807、marginalization398.200、IMU0.853），求解0.02075s且iterations9／NO_CONVERGENCE。RANSAC单轮较之前推进更远，但仍不能算到达或严格因果证明。

据原0.04s求解预算尚有余量，将唯一参数源`config/components/localization/vins_sim.json`的max_num_iterations从8调整为16，max_solver_time仍0.04；健康max_solve0.1、cost1.0、freshness等全部未变。这是优化器工作量调整，不是健康阈值放宽。`test_vins_config.py`2项与`test_localization_health.py`12项通过；文件名误调用的test_vins_session.py不存在，不计测试证据。repair17同二进制冷启动，仅该配置项变化，继续16m任务；额外迭代可能增加耗时，需要运行验证。连续成功计数仍0。

repair17在使能前失败：初始地面EKF局部原点收敛期间桥已锁定alignment_drift约0.169m；旧只读前检漏检bridge.ready，虽报passed，原生使能门仍拒绝且全程未解锁。随后新增观测订阅集中接入时raw VINS遥测最大接收间隙0.726s（source32.936→33.004），定位状态约0.606s间隙、propagated_stale锁定；不能直接认定订阅是根因。完整flight/metrics/hash见该run failure-analysis.json。尚未评价16迭代导航效果。

补齐桥初始化：仅DISABLED且实际落地、未解锁、无既有alignment故障时，允许重新捕获地面坐标对齐；PRESTREAM及后续飞行阶段固定不变，已锁故障不清除。真实节点3项（含7种地面对齐边界）和原控制11项通过，独立包构建1.73s通过，路径ego-bridge-ground-alignment-fix-20261021-01。repair18前检增加bridge.ready检查；观测者及flight probe先建立订阅、等待完整40s前检报告，再执行原5s稳定门／使能；减少飞行前临时订阅发现扰动，未更改原生门、健康阈值或任务。该启动顺序改变是实验变量，不能与17直接作算法A/B。

repair18：40s前检无定位锁定、地面对齐漂移0；RTF0.624、optimized最大接收间隙0.417s（启动发现阶段）。前检错误地要求bridge.ready（372次px4_preflight_failed），未使能。根据control_state.py现有enable明确require_preflight=False的流程，未解锁预发送→请求Offboard后才要求PX4 preflight。repair19纠正只读前检及probe条件：仅放行这一既有预发送前的状态，仍检查全部定位、融合、时效、地面对齐和唯一发布者；不改变桥、PX4原生解锁检查或任何健康阈值。18的FAIL为过严实验前检，排除飞行／优化器评价。19相同候选冷启动。

repair19：前检末尾连续36.63s通过，RTF0.620，成功进入Offboard／解锁起飞，但到source49.668时accel_bias_norm0.164875超过原0.15，保护降落并LANDED／上锁，未ACTIVE、未发目标。此前bias0.0568→0.0839→0.1298→0.1412，cost未越线，优化odom最大回执间隔0.161s，raw遥测最大0.338s。16迭代未显示足够收益，回到repair16曾接近终点的8迭代基线；不据单轮断言迭代增加导致偏置。

新0013隔离候选在原左右光流／前后向检查后、压缩右图向量前，用固定RIC/TIC构造完整essential matrix，使用现有F_threshold/FOCAL_LENGTH的Sampson误差拒绝不符合双目几何的匹配，左图单目轨迹保留。对齐外参仍唯一来自SDF生成的session yaml，非写死垂直差；无真值。仅固定外参模式使用，缺少／坏标定或向量大小不符不会读取越界。尚不能排除沿极线的错误匹配，也不能根据该补丁先验宣称根因已修复。

发现旧alignment-observer将numpy float32列表直接JSON编码，导致最终写盘失败；19及更早缺失的alignment-observation不能作对齐证据。后续仅将这些数值显式转float并保留异常日志；既有planner、flight、raw metrics与Gazebo真值报告独立有效。

repair20首次16m到达：action succeeded／position_yaw_tolerance_held，最终估计[15.878,0.030,0.864]m，正常触发降落并最终LANDED／上锁。地面同一源戳配对仅作一次固定SE(3)、scale1、无时间修补：世界IMU目标[8.122,0.043,0.922]m，真值三维最近误差0.11689m、原0.25m／0.35rad容差内连续1.20516墙钟秒≥1s；独立到达检查通过。真值名义机体球采样净空0.27853m，非连续扫掠验收。

严格全程健康仍未通过：LANDING从source94.092开始，95.836首次raw cost1.1845；此时真值机体已到地面z≈-0.013m，PX4稍后96.936确认landed、98.968上锁。首次cost1341.308=visual832.841+prior498.946+IMU9.521，bias0.0082、171输入/38双目/34长轨、9次迭代0.0131s。flight.json自身PASS只表示动作及落地，arrival-evaluation.json严格navigation_check_passed=false，不能拿原PASS冒充全程健康稳定。连续成功仍0。

repair21只新增合法范围内MPC_Z_VEL_MAX_DN=0.5（PX4源码元数据最小0.5；MPC_LAND_SPEED最小0.6，未越范围设置更低值），原上升限速0.5保留。目标、VINS8迭代、0012+0013、健康阈值全不变。检查原mc_pos_control源码速度约束并用真值下降速率验证实际降速，不能仅凭参数宣称修复接地残差。冷启动继续。

repair21再次到达并落地上锁：action succeeded；固定地面对齐真值3D最近误差0.09825m、容差内驻留1.36331墙钟秒。接地时仍cost越1，故严格连续成功0。首次越线source97.156，总cost977.943=prior425.079+visual551.489+IMU1.374，bias0.0175、110输入/34双目/31长轨，9次迭代0.0125s；真值同时机体z≈-0.0117m。真值0.1–0.7m高度实际下降速度中位-0.481m/s（20为-0.651m/s），表明0.5下降限速实际生效但未修复接地健康。

repair22：同二进制／同目标／同健康门，仅下降上限0.5→0.2m/s继续隔离SITL试验。该值低于PX4参数元数据建议最小0.5，非实机已验收设置；源码控制器使用正速度上限，没有运行时下限钳位，必须核对实际下降曲线与副作用。未把MPC_LAND_SPEED强设为元数据范围外值。真实常规到达已连续两次，严格全程健康仍未收敛；保留该区别。runtime-contract归档实际二进制／已安装own Python／公共配置／模型／世界和PX4哈希，后续复测逐文件比较，排除epoch/domain/run目录身份字段。

repair22第三次native与独立到达（真值3D最近0.07801m、驻留1.68937s）并落地上锁，但接地仍cost≈1.226锁定。仅降速并未修复，严格成功仍0，已恢复下降限速0.5，撤销低于元数据建议的0.2候选。

新渲染边界假设：现有SDF三个强度图相机与深度相机共用near=0.2m。相机落地高度约0.067m，以fy≈337和图像底边推导最近地面前向距离约0.095m，被该近裁剪面删除；截图21的左图底部也可见平坦背景带。下降时裁剪边界扫过地面，可能导致大量非物理特征消失／重建，但尚无因果飞行证明。将infra1/infra2/color近裁剪面改0.02，深度near0.2及所有内外参／发布频率／几何碰撞不变，统一在simulation/models/d435i/model.sdf维护；所有会话重新生成model哈希，不拼接旧epoch。新地面投影约束回归+原几何共4项、VINS配置2项、world生成3项及结构检查通过。repair23同算法新模型冷启动，原健康阈值不变；需要核对实际图像、起飞与导航，不能先称模型修复成功。

repair23：新near clip实际地面图像灰色裁剪带移除，前检稳定37.48s／RTF0.611通过，原动作再次succeeded并落地上锁；独立真值最近0.2285m但容差内驻留只有0.339s<1s，不能算独立到达通过。接地后仍normalized_cost锁定，near clip不是充分修复。firstbad96.824总cost909.051=prior604.186+visual268.656+IMU36.210，bias0.0213、35双目／35长轨；前四帧cost330.8→392.5→506.2→676.7，真值机体均已接地z≈-0.013m，优化却仍持续移动，值得查惯性冲击积分。严格计数0。

repair24不再调算法／速度／模型，仅在既有Gazebo只读评估器同时订阅原生D435i IMU，采集接地前后比对imu积分∆v与真值姿态位置导数；无ROS发布、无真值回馈。已核对安装libgz-sim8=8.14.0、libgz-sensors8=8.2.2，官方对应tag的Imu.cc直接读取当前physics LinearAcceleration，ImuSensor.cc加重力后按自身update时刻发布，没有在该层跨物理tick积分平均。运行物理步长0.004(250Hz)而D435i IMU200Hz，冲击采样混叠仅是假设，必须以24数据验证。源码参考：
- https://raw.githubusercontent.com/gazebosim/gz-sim/gz-sim8_8.14.0/src/systems/imu/Imu.cc
- https://raw.githubusercontent.com/gazebosim/gz-sensors/gz-sensors8_8.2.2/src/ImuSensor.cc

repair24原始IMU证据：20,187个样本的源间隔4ms×15,139、8ms×5,047。接地±0.5s真值竖直∆v=+0.200150m/s，而原生IMU积分仅+0.000177m/s（误差-0.199973m/s），窗口内最大|az_world|仅0.00954m/s²；±0.3／1s结论相同，支持漏掉制动冲量而非单纯求解器慢。动作到达及真值驻留通过（最近0.1229m／1.2187s），落地上锁但健康仍失败。

独立最小落体对照`artifacts/runs/imu-contact-sampling-20261021-01`：无ROS/PX4/VINS/控制器，只D435i刚体自由落体、地面、原生IMU和只读odometry。4ms／5ms步长各测试1m、0.96m初始高度。4ms+200Hz、0.96m时真实∆vz3.8622而IMU=-0.50948，误差-4.37168；5ms+200Hz同高度为3.84750对3.79850（误差-0.0490，保留一tick离散误差），1m两步长均捕获冲量。说明4ms采样存在与接触相位相关的整次漏冲量，不能仅靠降低速度修复；对应原生加速度直接按自身频率抽样的实现。原生OdometryPublisher twist有平滑，离线速度改为真实位置导数；不把其平滑twist冒充瞬时速度。analysis.json含4份原始数据sha256，边界断言通过。

repair25仅增加`config/components/simulation/vio_physics_probe.json`，run-local世界physics step0.005／update200，与同一D435i IMU200Hz对齐，其他控制、几何、重力、算法、目标和健康门保持。overlay验证rate*step=1、碰撞XML哈希前后相同，记录原新physics与配置哈希；canonical PX4 world和来源未改。继续完整16m导航并同样记录IMU，需验证PX4不同步长下的实际控制／时钟／数据时效，最小落体成功不能替代SITL。

repair25前检稳定37.28s／RTF0.593通过，使能解锁后尚未实际离地，桥因external_odometry_stale进入LANDING，后对齐漂移0.151；原定位稍后telemetry_stale，未ACTIVE／未发目标。raw遥测最大0.472s，odom多次0.20–0.25s、最大0.370s接收间隙；原生降落最终LANDED上锁。没有完成接地冲击验证，也不能以一轮断言5ms物理不可用。为保留多轮已能导航的PX4物理时序，26恢复原4ms physics，单D435i虚拟IMU更新200→250Hz，使每个物理tick都采样；属于SITL等效传感器频率，不宣称实机D435i配置已验证。

同一最小自由落体测试新增4ms+IMU250Hz的0.96m／1m两高度，两者均捕获冲量，积分误差约0.0392m/s，断言<0.1通过；原200Hz相位漏冲量误差4.37m/s仍保留。SDF唯一更新源，bridge／VINS／内外参／图像／健康门不变；26启动前读取实际生成world step与模型IMU rate，强制rate*step=1，否则拒绝运行。几何回归新增飞行物理步与IMU周期一致性，共5项，VINS配置2项及结构／diff检查通过。重新记录所有runtime哈希，严格成功仍0。

repair26：IMU250/physics4ms启动契约通过，前检连续37.67s通过；起飞未ACTIVE，桥73.7墙钟秒附近external_odometry_stale，最终落地上锁。原定位全窗仍TRACKING，optimized原始接收最大间隙0.240s<0.3。25／26桥detail在第一次LANDING前分别记录clock_mapping_rate_out_of_bounds（25共19次、26共5次），不是简单原始定位停流。

检查time_mapping.py：to_px4先通过64样本窗口_fit验证配置速率[0.1,10]；随后_monotonic_at_ros_time又把相邻两条clock接收间隔比值要求在同一范围。DDS成批送达时局部接收速率不等于仿真RTF，可以在整体时钟正常下丢弃有效EV，积累mapped里程计间隙。仅将局部插值改为检查有限且正向的接收时间，仍用真实接收时刻插值、不外推；整窗速率范围、source age0.35、odom receipt0.3、clock stall、rollback/future等限值全部保持。严格回归：burst区间速率0.001但整体合法时source龄0.3499接受、0.3501仍拒绝；非递增局部时间拒绝；原真速率越界／回退／过期测试全保留，共22项通过。原fault/landing3项和control11项通过，独立包构建1.89s通过，候选ego-bridge-clock-burst-fix-20261021-01。27只换此桥构建，IMU250／物理4ms／所有原门限和16m目标保持。该解释有源码及状态时间线支持，仍须SITL验证，未宣称两轮所有rate错误均已逐样本复原。

repair27完整16m原动作成功且接地后仍TRACKING／地图有效，IMU250的接地±0.5s真实∆vz0.201374、IMU积分0.201346，误差仅-0.0000280m/s；原200Hz漏冲量故障已在这一个全栈接地窗口消除。但原真值到达驻留仅0.513s<1，且PX4未自动上锁，整轮FAIL，不计三连。

进一步审计发现PX4实际cwd是run/px4_sitl_default，而复制脚本只删了rootfs下参数文件，顶层parameters.bson／backup仍链接历史193状态，MPC_Z_V_AUTO_DN=0.2被继承。原生落地检测要求下降命令>=1.1*LNDMC_Z_VEL_MAX(0.25)=0.275，原生uORB轨迹一直0.2，因此低油门／零速度／低旋转也不能ground_contact。在当前真实已接地时将正常自主下降速度恢复1.5后，PX4自行ground_contact→maybe_landed→landed→disarmed；未强制上锁或改检测阈值。

审计局限：最初host删除root-owned链接因权限失败，随后native参数调整发生在彻底隔离前，历史193可变BSON可能已被自动保存修改。之后在容器内成功脱链成run-local文件，记录source hash和该事实于27 parameter-isolation-discovery.json；未猜测回填历史内容，既有固件二进制／已关闭ULog不受影响。01–27的新进程／新VINS epoch仍有效，但不得当作PX4参数完全干净的独立冷启动。旧source参数文件今后只读，新的全量冷启动从空参数／任务状态开始。

根修复同步至正式tools/run_gpu_vio_sitl_runtime.sh：新tools/prepare_px4_run.py共享隔离复制，排除顶层和rootfs参数BSON／dataman，eeprom／log为新空目录，只读build资产继续链接；拒绝覆盖目标或嵌套源目录。单元测试实际写新run参数／etc并断言源文件不变、历史状态不导入，拒绝重复和嵌套，1项多断言通过；bash语法通过。28首次从空BSON/任务状态启动，原下降限速候选撤销、只保留上升0.5。原生参数审计确认autoDown1.5、landSpeed0.7、maxDown1.5、落地阈值0.25、纯EV/GPS0正确。发现额外eeprom空链接（没有历史内容），运行中已脱链成空目录；28作为验证轮，之后统一使用共享隔离器重复资格轮，避免将调试轮冒充三次固定入口冷启动。

27说明原生0.25停止容差可能在真值刚进0.25窗时即结束，现将原生位置停止容差收紧到0.1，在同一room_crossing_goal.json新增verification_position_tolerance_m=0.25明确保留原独立物理验收线；yaw和1s驻留线不变。不是放宽实际误差或定位健康门。28继续验证，严格成功计数仍0。

29（共享隔离器首轮）：独立参数、纯EV、原门限启动并导航／正常降落，定位全窗TRACKING；但native goal_timeout，源估计终点[15.86516,0.00565,0.88634]距请求[15.96810,0.00286,0.88554]约0.103m，未达0.1m，严格FAIL。最后三次样条控制点加权(1,4,1)/6的真实端点约15.8658m，正对应悬停位置；不是传感器停流。原EGO calcTerminalCost数学公式正确，但终点为软惩罚且rebound允许末3点自由，轨迹时长结束即WAIT_TARGET，没有确保达到更严任务容差。不能据末控制点在目标上就认定曲线到达。

0036候选：canonical固定提交和15补丁重新物化、保留已用0035 yaw边界；对local_target_vel=0的终止型目标，在rebound优化前将最后3个三次样条控制点设置为目标并排除其优化变量，表示端点＋末速度＋末加速度硬边界，end_acc同步0；refine前保持相同边界，原碰撞／可行性校验继续运行。移动型局部目标保留自由末端，不对发布后的轨迹补写直线或绕过检查。三文件补丁按`patch --binary -p1`重放逐字节哈希一致；GPL3许可／源commit／基准哈希／应用顺序归档。新bspline_opt+ego_planner对#297依赖单任务构建3min2s通过；实际C++ UniformBspline断言端点精确、末速度/加速度0、起点不变、移动目标不改、短矩阵拒绝，通过。源锁／canonical vendor未改，30使用新两包冷启动并验证发布样条实际末端，而非凭源码先判通过。三连从新版本重新计数0。

30新0036版本首轮完整通过：native action／落地上锁PASS，原真值0.25m窗驻留2.63053s、最近三维误差0.03384m；定位invalid0、map/nav故障0、控制链所有publisher计数1，真实样条末端距请求1.7e-18m、末3控制点平坦误差0；名义包络采样净空0.41115m，50Hz真值无缺口。相同算法／配置哈希600914...、源历史可变文件hash未变，qualification.json九项全通过。单轮非完整P0–P6/A–H验收。

31在使能前检查脚本退出时SIGABRT（terminate called without active exception）；settled-imu.json已记录真实ready=true／106样本／9.8，但Python Gazebo Node解除订阅后解释器退出触发原生绑定崩溃，cleanup使PX4启动中止。无VINS／goal／enable／解锁，保留为启动失败，不拿ready文件覆盖进程失败，也不宣称已三连。故三连从固定启动器修复后重计0。

新增标准库tools/wait_sim_imu_settled.py，调用原生`gz topic -e -t /sensors/d435i/imu -n200 --json-output`，真实解析有限向量；只在连续30个范数仍处9.5–10.1且CLI成功退出时ready，超时／非有限／缺字段／native失败均拒绝。参数集中config/components/simulation/imu_settle_gate.json，原判据与25s超时不变，避免Python加载Gazebo绑定而非吞掉崩溃。解析／原判据3项通过；独立physics-only真实CLI三次均读200样本、范数9.8、返回0，日志在imu-settle-cli-check-20261021-01。32–34保持该启动器、同飞行算法参数再冷启动。

静态回归归档首次attempt1中宿主6项脚本通过，但4项ROS脚本因31容器已退出而未运行，不能计为代码回归失败或通过；原始失败输出保留，后续在活跃容器重跑并单列新结果。

固定启动器后的32九项qualification全部通过：原生action及正常落地上锁、独立真值最近0.137892m／驻留1.798980s、定位invalid0、地图导航故障0、唯一控制发布者、采样名义机体净空0.233366m、50Hz真值连续；真实末端误差1.1e-16m且末速度／加速度为零。最终冻结契约a0f26c236a13510ef7456053c6bb9e2d4ebf90729de1f898f455b9abb2088ec5，所有运行文件和历史源可变文件hash未变。32–34计数1/3，33启动中。完整静态回归11脚本88项通过，tests.json单列于cpu-navigation-checks-20261021-051；包含此前容器退出未运行项的真实重跑。

33全链FAIL：前检／起飞ACTIVE后px4_frame_alignment_drift锁定并保护降落上锁，goal_timeout；连续计数重置0。真值／VINS同戳高度在起飞转折附近仅约1–2cm差，而PX4高度估计与传感器位置差在运动中增大，源时效仍合法，未以真值纠正状态。故不能认定32后已稳定。35只将上升cap0.5→0.3m/s，试验减少起飞瞬态，其他算法、导航速度、健康门和下降／落地参数不改；native参数审核改读取同一配置并容许float32表示误差。重新冻结哈希并独立35–37三连，保留33所有失败证据。该调参尚不证明估计动态问题已根除。

35上升cap0.3启动／前检正常，50墙钟秒起飞观察窗结束时仍未ACTIVE，真值机体最高0.2991m、VINS相对最高0.1984m，探针主动取消并正常落地上锁；无导航目标，不计通过。36起飞观察窗单独延长90墙钟秒以完成慢起飞；原数据新鲜度、对齐、定位、地图、导航到达／驻留和降落判据全保持。该超时不是核心健康阈值。35原日志不改。

36在90s观察窗内ACTIVE并实际导航约3m，随后再次px4_frame_alignment_drift保护降落上锁，目标最终goal_timeout。上升cap0.3不是充分修复，严格计数0。ULog同戳显示PX4竖直状态与VIO／真值出现运动相关偏差，水平仍接近。当前GZBridge.cpp imuCallback第451行取hrt_absolute_time，将callback时刻同时作sensor_accel/gyro timestamp_sample而未读取原生header；这只是待验证时序假设。39保持相同飞行配置，另加原生PX4 Gazebo IMU只读订阅，与ULog未过滤sensor_accel数值逐样本匹配以测时间误差，禁止在线真值校正。

39使能前探针读preflight.json部分写入而JSONDecodeError（最终前检真实passed），没有解锁／目标，计失败。原生PX4 IMU静止24组accel和24组gyro与ULog逐值精确匹配，header与timestamp_sample误差均0，不能据源码怀疑即认定时间戳问题。40继续运动段诊断；前检报告改临时文件完成后原子replace防止读半文件，原判据完全不变。

40完整九项通过：真值最近0.07457m／驻留2.82282s／定位invalid0／采样包络净空0.32099m，正常落地上锁。原生PX4 IMU运动全程accel和gyro各95组浮点值精确匹配，source header与ULog timestamp_sample差全为0，不支持本轮时间戳延迟假设，未修改PX4源码／二进制。离线33／36原ULog视觉竖直速度对真值RMSE0.00570／0.00337m/s，PX4输出为0.08965／0.05733、最大0.2679／0.2809；output tracking误差只约0.03，EV速度innovation明显。41单独将VIO bridge上报速度方差0.04→0.01m²/s²（标准差0.1，等于原PX4 EKF2_EVV_NOISE默认下限），提高视觉速度融合权重，不改位置／姿态方差或健康门。这不是实机协方差标定，待完整SITL；41–43重新冻结同配置、独立空参数三连，0/3。上升仍0.3、起飞观察90墙钟秒，导航速度0.7／加速度1.5未改。

41新融合候选九项全通过：真值最近0.034898m／驻留2.942242s／定位invalid0、map-nav故障0／名义包络采样净空0.330215m，正常落地上锁；真实样条末端精确且零末速度／加速度，控制各唯一发布者。PX4原生ULog实际三轴velocity_variance唯一值0.009999999776（float32的0.01），最大记录对齐漂移0.06803m。候选同一契约43a25360d37bafccbe890484806b786a62bcbae345f5fadcabc15621adc5095a，源可变文件未改。7项VIO profile回归通过；三连1/3，42启动。

42距目标约0.8m处normalized_cost=1.0059295锁定取消，保护降落上锁，三连重置0。原生9次迭代、solve0.033s、54长轨、bias0.03897；首次对应rawstamp97.252s，总cost1320.52=prior383.07+IMU2.94+visual934.52（70.77%），2610残差，normalized=sqrt(2cost/res)。下一帧565.44／2464已恢复，但不据此撤销保护或忽略失败。最大记录对齐差0.10451m<0.15，新的EV融合尚未在本轮再触发旧对齐故障，但不宣称根除。44–46仅进一步将EGO速度0.7→0.5m/s、加速度1.5→0.8m/s²，试验更温和的图像运动；到达0.1native／0.25true／yaw0.35／dwell1s及原健康门保持，目标timeout仍120s。只读观察器延至380wall以覆盖较慢完整任务，不改变控制或保护。新契约744324e9aca12b903925c2138ab0bb4452ade79a06b43336265b03794f8d77c6，三连0。

慢速任务预算复核：42原0.7速度在低RTF轮目标段约100wall s，降低至0.5按1.4倍需约140wall s，旧120任务deadline不充分；故只将room_crossing_goal timeout120→180wall s，独立位置／yaw／驻留、所有时效／健康／保护数值不改。44尚未PRESTREAM／使能时已主动停止，不当作已飞行或成功。统一新47–49冷启动；全量契约a3396eff6108c4eec1cfebd94fe4025568dd6673aa009b1bc45d0ab482f89bb5。低动态bringup7项回归通过。

47使能前FAIL localization_or_px4_freshness_not_stable_before_enable，无service调用／无解锁／无目标。前检先passed，随后raw VINS遥测接收出现0.630816wall s间隙（source只前进64ms，该求解0.0284s，非solver超预算），健康原门telemetry_stale锁定，地图清空。前检更早还有0.6678s初始化间隙。低动态参数尚未被实际飞行验证；禁止因保护发生在起飞前忽略失败。开始在只读失败会话读取真实相机图片，原生OpenCV4.6比较16／4／1／8线程的四次LK批处理尾延时；仅离线时序诊断，不作导航证据。

真实640×480左图+离线8／2px运动、实际45特征（请求上限180）、四LK原生OpenCV4.6的100次计时：16线程p99=3.644／max5.564ms，4线程2.730／3.151，1线程5.835／5.891，8线程2.937／3.424；仅当前负载单图微基准，不足解释整次0.63s阻塞。50–52改运行OpenCV4线程以减调度竞争、再次实测当前完整修复版本，16→4不需改算法或构建；旧4线程失败发生在clock-burst／接触采样修复前，不能直接作为该新版本结论。其余低动态／EV方差／到达／健康设置全保持；新契约6527e6b216ce529a7cfbe6852beb9713d13ef9cf6e115e706f5073b939392128。严格0/3。

50新4线程／低动态配置九项全通过，实际OpenCV threads=4已从进程日志核对；真值最近0.11957309832041277m、驻留3.2536830230001215s、名义采样净空0.3543017010914114m，定位地图全程有效并正常落地上锁。契约6527e6...保持、源可变hash未变。三连1/3，51继续相同配置。

51第二次相同配置九项全通过：真值最近0.12566980742929956m／驻留2.650520378998408s／名义采样净空0.3151721767903611m，定位地图全程健康、正常落地上锁，原生实际样条末端与健康／控制检查通过；运行和历史源hash未变。三连2/3，52继续。

52第三次九项全部通过，真值最近0.049863m／原窗驻留3.694413s／名义采样净空0.353357m，定位地图健康至LANDED，上锁。50／51／52最终固定契约6527e6b216ce529a7cfbe6852beb9713d13ef9cf6e115e706f5073b939392128，三epoch唯一、所有运行／历史源hash保持，脚本身份归一化一致。ULog三轮导航EV位置／高度／yaw／速度融合持续1、GNSS0，样本58／59／58；实际方差0.01、OpenCV4。当前房间检查3/3收敛，P4–P6／正式S1–S6／A–H不升级；默认vendor锁仍未推广。新增可读摘要progress/evidence/cpu-navigation-convergence-20261021-051.md及机器证据最终索引，Gazebo/RViz保留52落地上锁窗口。

最终检查：python3 tools/project_status.py PASS（仅结构）；git diff --check PASS；bash -n tools/run_gpu_vio_sitl_runtime.sh PASS；git status --short --branch完整结果归档final-checks.json，原有大量已暂存／未跟踪工作保持，未提交或推送。只捕获本轮Gazebo／RViz应用窗口，不捕获私人桌面。任务后补充只读状态快照单列于52/post-landing-readonly.json，不回填三次飞行验收区间。

最终完整性补检：50／51／52三轮mission与Gazebo只读评估六个进程均exit0，93个冻结运行文件无变化；52任务后只读快照定位valid、map input_ready／1641points、bridge LANDED／armed=false／control_enabled=false。idle preflight-ready=false保留原始值，不等同下一次使能通过。净空范围明确为模型z>0.5m且排除地面。
