# #499 N12 固定输入基线：原RPE失败复现

当前数值源码隔离构建成功；仅离线可靠订阅与native回调/双目消费trace不同。#498 MCAP的30885IMU、左右各3744图像均完整进入native回调，全部3744对双目被同步处理，catch-up丢帧0，外部输入监视与原bag源戳SHA完全一致。

固定原PRESTREAM源时刻一次scale-one SE(3)后，目标段RPE10平移P95=0.059407589m，原真实飞行0.059407374m，差异约0.000000215m；该失败在完整输入下复现。高误差窗起点10–20s的世界位移误差P95=0.060931m、初始姿态作用P95=0.010478m；求解139/151次NO_CONVERGENCE，solve P95=0.023652s。定位误差的位移部分占主要贡献，不支持通过丢帧/统计阈值处理消除它。

下一单变量离线假设已声明：同一MCAP、同一binary、max_cnt220/stride2/IMU参数/40ms solver预算固定，仅max_num_iterations8→16。#453曾在旧max_cnt180/另一数据上未解决精度，负例保留；本次由于当前220特征/绕障数据及高迭代限制比例而检验。须核对每个native输入/processed双目与所有原VIO阈值，未通过不部署。在线候选未改，正式次数仍0/3。

[实际native审计](../../artifacts/replays/n12-20261029-499-fixed-input/baseline498/native-input-audit.json)、[完整数值与分解](../../artifacts/replays/n12-20261029-499-fixed-input/baseline498/evaluation.json)、[单变量实验声明](../../artifacts/replays/n12-20261029-499-fixed-input/iterations16-experiment-plan.json)。本次是离线诊断，不计正式飞行。
