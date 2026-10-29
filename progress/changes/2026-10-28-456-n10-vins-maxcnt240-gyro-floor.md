# N10.3/#456

在max_cnt240下单独降低gyr_n的隔离离线候选触发VINS同步追赶丢弃1对双目帧，输入流不完整；IMU队列峰值74、解算最大43.983ms，超过原40ms预算，严格门限状态为INSUFFICIENT，不部署。共同网格误差值不作通过依据。审计确认VINS estimator.Vs世界速度评估口径有效，Gazebo真值raw twist另由位姿中心差分处理。详见[证据](../evidence/n10-vins-maxcnt240-gyro-floor-20261028-456.md)及原始产物目录。下一步只测中间max_cnt=220、保持原gyr_n及其余基线参数；若原始完整门限或40ms负载边界仍未满足，则停止max_cnt调参，转入视觉前端/估计器根因分析。对话：[记录](../../collaboration/dialogues/2026-10-28-456-n10-vins-maxcnt240-gyro-floor.md)。
