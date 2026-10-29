# N10.3/#452：正确SDF gravity未改善剩余VIO门限

仅g_norm9.80665→9.8m/s²；实际world SDF gravity=9.8，其他binary/solver/noise与449 protocol固定。两案例真实native callbacks及processed stereo timestamps完全匹配，全部39181IMU/4749对同输入。运动RPE10p95 0.060494706→0.060501069m；保持速度p95 0.015166346→0.015168653m/s。变化约微米/微米每秒，支持正确物理配置但不解决既有失败；此前#439结论在完整native协议下得到确认。不把候选推广为精度修复。

下一#453依据完整native baseline telemetry中1788/2364次达到原8迭代上限，而solve p95约25.0ms、max33.98ms仍在40ms时间预算内，只改max_num_iterations8→16；原参数与验收标准保持，确认每个原生输入/处理帧后比较。无飞行，故障后校准排除，N10.3未完成。

产物artifacts/replays/n10-20261028-452-vins-gravity-exact及对应prepared。
