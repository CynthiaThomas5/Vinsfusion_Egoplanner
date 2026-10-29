# N10.3/#432 真实plan_env包隔离构建与类级验证

## 结果

已将当前完整plan_env包复制成baseline/candidate两份独立source/build/install。主工程在构建容器内只读挂载；只有/candidate独立挂载可写，构建使用固定镜像、network=none、2 CPU限制、CMAKE并行1。两份包均成功全新编译（各约1分8秒），共享依赖来自已有ROS/install，因此不是N10.5完整干净重建。

测试不再使用简化GridMap支架：复制的真实header仅加入test-only friend声明，夹具直接初始化真实MappingParameters/MappingData并调用真实GridMap::clearAndInflateLocalMap。两份源码的CMake仅额外添加测试target；测试不初始化ROS节点、不创建任何topic publisher。ldd验证实际加载/candidate/baseline或candidate/install/plan_env/lib/libplan_env.so，排除了误用当前运行库。

同样10个真实类案例（六面halo、正/负控制、两项边界alias）：baseline失败8项、test exit1；candidate全部通过、exit0。当前主工程grid_map.cpp SHA与#431基线完全一致，当前install/libplan_env.so SHA仍与#428 runtime-contract相同。候选未部署。

## 修复候选与验证范围

候选与#431一致：重建当前更新框inflation时，从扩展inf_step的source halo读取raw occupied；在toAddress前逐轴裁掉非法inflation目标，防止flat index alias。没有更改raw occupied/free/unknown判定、inflation数值或起飞/健康策略。

此验证支持真实库的编译与局部状态不变量；没有执行真实深度回调/ROS消息融合、planner联动、动态负载或SITL，不能证明#428唯一根因或飞行修复。新source扫描范围的性能影响仍需代表性负载校准。

第一次构建在编译前因固定colcon不支持--allow-overriding退出2，错误日志保留；删除该可选参数后两份构建成功。现有deprecated ROS ConstPtr编译警告保留，无编译错误。

## 产物与命令

目录：artifacts/n10-prepared/n10-20261028-432-isolated-plan-env/。

- prepare.py：复制、基线SHA验证、候选patch dry-run/apply到隔离副本、加入test-only fixture。
- build_and_test.py：固定镜像隔离编译、ldd核对、实际类测试。
- manifest.json：源/patch及生成库、测试二进制SHA；ros-test-results.json记录退出码和装载库。
- baseline-ros-build.log、candidate-ros-build.log、各自ldd和ros-class-test日志。

命令：python3 .../prepare.py；python3 .../build_and_test.py。源码不重复覆盖已有准备目录。#432构建driver/session47069已终止exit0，不是运行会话停止。

## 当前停止条件

当前#428监护session41790仍活跃，最新r12仍unsafe_wait。此前一次性disarm授权已用于#391，尚无当前#428新授权。已连续三个N10.3 Goal轮次核验同一真实安全阻塞；期间完成#429–#433全部直接相关离线诊断和候选验证。下一必要动作是当前会话安全收尾，再部署候选、进行新版本深度/规划/轨迹与剩余故障校准；这些不能用当前隔离编译或旧归档替代。

保留当前控制栈和只读监护，不新飞、不修改活动runtime源码/install。N10保持in_progress，N10.3未通过；不计N15/N16正式次数。

对话摘要：../../collaboration/dialogues/2026-10-28-432-n10-isolated-plan-env-validation.md
