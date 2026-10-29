# N10.3/#449：原生完整输入资格及原指标复现

隔离vendor副本仅将native IMU/stereo订阅BEST_EFFORT→RELIABLE，depth仍2000/5；原discard/stride2/solver8/0.04/噪声/g及#448只读trace保留，实际构建45.3s通过。配合可靠bag writer与监视器，完整回放后native callbacks IMU39181/左右各4749、源戳SHA全部匹配原bag；4749对原始立体图全部processed，catch-up drop=0，image队列保守前缀高水位1/1。

这是首次直接记录的完整原生输入证据。原指标复现#439基线：运动RPE10p95=0.060494706m，保持速度p95=0.015166346m/s；原0.05m/0.01m/s仍失败。说明接收首帧差异可区分，但即使完整输入原估计误差仍存在。可靠订阅仅限离线可靠writer，不能直接接当前在线BEST_EFFORT传感器源；主vendor/install不变。

静止校准：PRESTREAM前4s的1001条IMU，gyro均值近0（最大绝对均值约2.55e-16rad/s），std最大约1.73e-12rad/s，SDF未加零偏/噪声。仅支持已知理想SITL的校准假设，不是真机PSD。另对#442作离线RPE分解：运动10s世界位移差p95=0.05338m、初始姿态对真实位移的影响p95=0.02719m；不能把误差全归因yaw，也不以truth替换输出声明修复。

下一#450：隔离真实VINS实现增加一个已校准理想仿真gyro bias软先验（mean0、正sigma1e-5rad/s模型/积分floor），其余原参数固定，共享449可靠输入与trace，复用完整baseline。它不是健康门或硬固定bias；只测试单个最老state先验、不积入历史边缘化；实际输入/公共时间/原指标都须复核。新factor未纳入旧诊断cost分桶，若后续采用需完整实现。无在线部署/无人机飞行/故障校准，父N10.3未完成。

产物artifacts/replays/n10-20261028-449-vins-native-reliable及对应n10-prepared（源diff/license/commit、实际build、raw估计、native trace/audit、静止校准、RPE分解）。
