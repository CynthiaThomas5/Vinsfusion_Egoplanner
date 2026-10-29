# N10.3/#453：增加求解迭代未达到原运动RPE门限

只把max_num_iterations8→16，solve预算0.04s、同VINS二进制、全部噪声/重力/strides配置、可靠原生输入固定。实际native callback记录IMU39181、左右4749全部与bag stamp fingerprint一致，两组处理全部4749对立体图且源戳相同，image队列保守prefix HWM1。配对比较得到全指标和同源输出支持。

NO_CONVERGENCE从1788/2364降至158/2364，solve p50/p95/max由15.05/24.98/33.98ms变为16.19/32.15/43.21ms；原40ms预算下有部分求解时间超限。运动RPE10平移p95从0.060495降至0.057522m，仍高于0.05；保持速度p95从0.015166到0.015124m/s仍高于0.01，运动位置p95由0.106709变为0.111836m。原始绝对误差/yaw与旋转RPE已有支持项均应用同一未改draft gate。候选不部署。

诊断增迭代能收敛更多求解却没有足够的位置精度收益，还将若干求解推过现有预算；不能再靠盲目提高iteration或删门限。下一#454复核此前每帧特征候选：上次#440因为只读输入监视缺失1 IMU、且原生consumetrace未知，不足严格因果。本轮用#449同一完整native可信输入/trace，仅将VINS已跟踪帧enqueue stride2→1，记录完整processed源戳及队列。若source输入/solve budget不支持则明确不部署。

产物artifacts/replays/n10-20261028-453-vins-iterations16-native及对应prepared，真实输出/严格native输入SHA/公共source-time/全原指标报告。无无人机飞行/在线改动，N10.3仍未通过。
