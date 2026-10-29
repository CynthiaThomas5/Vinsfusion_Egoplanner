# N10.3/#439：重力单变量离线回放，未解决剩余误差

> #447补充限制：此前完整输入校验来自外部监视器，不等同估计器原生实际接收/处理帧等价。相同配置已发现处理帧相位差异；参数结果保留为观察，严格因果修复支持待原生receipt/processed/drop记录。没有因此部署候选。


同一#436传感器MCAP、同一已核对原VINS二进制和相机/外参/求解参数，仅g_norm9.80665/9.8不同，epoch/输出目录独立。使用network-none隔离容器，不运行PX4/planner，不重飞、不改在线参数。科学假设为“匹配实测重力是否足以解决剩余RPE/保持速度误差”。

首次播放器启动阶段漏约0.8秒输入，两个monitor指纹不一致，判为不足并保留baseline/world_gravity原目录。修正离线协议为start-paused，发现所有输入publisher后再统一等待2s并Resume；重做baseline_full/world_gravity_full。

最终两组均完整收到IMU39181、left4749、right4749条，起止源戳与全部源戳SHA逐话题等于原MCAP；处理位姿均2364条、源戳SHA相同、原任务时间窗均覆盖。配置去掉epoch/输出目录/待测g值后字节完全一致，左右标定文件相同。原bag、源码与在线参数不变。

| 项目 | 原g_norm9.80665 | 匹配world的9.8 |
|---|---:|---:|
| 运动RPE10平移p95 m | 0.060494706 | 0.060500849 |
| 保持速度误差p95 m/s | 0.015166346 | 0.015168654 |
| 运动位置误差p95 m | 0.106709032 | 0.106626246 |

两组都未过原0.05m/0.01m/s草案。此数据不支持将g差异当作这两项失败的充分解释或修复；不推广为所有重力误差都无影响。原baseline结果与#438原运行复算接近，支持该录包可复现对应残余。保持速度峰值在原completion后约16s，主要为横向：真值约[0.0067,0.0154,0.0013]m/s而VINS近零，不能解释为单纯z方向重力范数偏差。没有通过参数变更或阈值放宽追通过。

验证：真实两组完整离线VINS回放、独立MCAP输入指纹、实际输出与固定源时间窗/RPE/速度评估；脚本py_compile通过。此为离线证据，不是新SITL或正式次数，#438的576单测/两ROS集成不重复冒充本项飞行。两个回放容器已退出，所有子进程仅离线估计器/播放器。

产物artifacts/replays/n10-20261028-439-vins-gravity：result-full.json、各case actual alignment-observation/evaluation、expected-inputs、config-difference-audit、初次不足结果和日志；冻结脚本位于artifacts/n10-prepared/n10-20261028-439-vins-gravity-replay。机器汇总见同名json。

下一#440：源码Estimator::inputImage确认FT处理每张图，而MULTIPLE_THREAD只enqueue每第二帧。明确新假设：更多同输入视觉约束可能降低横向漂移/RPE；先隔离构建仅stride2→1的候选并回放，保持g_norm原值，不部署、不降低指标。需同输入覆盖、公共源时间评估和资源/队列证据，不因新假设就称已修复。父N10.3仍未完成。
