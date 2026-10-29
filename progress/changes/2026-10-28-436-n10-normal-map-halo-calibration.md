# N10.3/#436：正常导航校准完成，父目标未完成

实际运行0060后的正常16m路线/方箱重规划/20sim s保持，无故障注入。action成功，禁止接触0，正常落地上锁后受控停止exit0。目标前身份冻结，记录器协议与实际unit_cylinder_4 ROI纠正；五类只读记录器补外部信号部分数据保存。

离线发现正常结束后READY参考遗留，以及不同评估器真值参考不一致。原严格收尾false和初版报告保留；新增正确IMU参考审计，不把旧数值直接用于N10冻结。修正后采样净空0.438014m，运动RPE10 p95=0.060495m、保持速度误差p95=0.015137m/s仍未过草案。无阈值放宽。

验证：48项observer/capture/acceptance单元通过；实际ROS中断烟测初次capture阻塞，#437修复后r02五记录器均exit0、部分报告存在且safe=false。562项全测试及两个ROS集成、17包构建见#437记录。停止原因：本次正常飞行及证据审计子项完成，仿真已停止；N10.3保持in_progress，下一项#438统一参考点/评估器并复算预算，不以此关闭Goal。

证据：../evidence/n10-normal-navigation-calibration-20261028-436.md、同名json；产物artifacts/runs/n10-20261028-436-normal-map-halo-calibration。对话：../../collaboration/dialogues/2026-10-28-436-n10-normal-map-halo-calibration.md。
