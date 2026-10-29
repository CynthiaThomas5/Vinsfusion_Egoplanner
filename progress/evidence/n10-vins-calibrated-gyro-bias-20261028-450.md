# N10.3/#450：软gyro-bias先验改善yaw但未解决原失败

隔离原449可靠native/trace版本，只加已知理想SITL gyro bias Gaussian prior（mean0、sigma1e-5rad/s，最老state一次、不积入边缘化）；无硬固定bias/控制或健康门。真实45.2s构建通过；原源码/install未部署。静止测量和SDF支持理想模型假设，不是真机PSD，新factor尚未纳入旧cost诊断分桶，不能当最终实现。

原生callbacks全部IMU39181/左右各4749、4749对全处理，两组完整实际输入/processed源戳SHA一致，公共时间可比。相对449baseline，运动RPE10p95 0.060494706→0.061107706m、hold速度p95 0.015166346→0.015411463m/s，原0.05/0.01仍失败；yaw p95运动0.748869→0.192215deg/hold0.891009→0.217656deg，位置p95运动0.106709→0.099181m。确认gyro bias先验能影响yaw，但不能把剩余运动/hold误差全归因yaw；本候选不部署。

下一#451回到无新先验的449实际完整native binary，只改gyr_n0.001→1e-5的正数仿真噪声floor（#442更强gyro权重曾部分改善，静止理想IMU数据给物理校准依据，非真机PSD）。原其余参数、原阈值和actual-native验证协议固定；不恢复经验门、无新飞行/故障校准。父N10.3未完成。

产物artifacts/n10-prepared/n10-20261028-450-vins-calibrated-gyro-bias（实际源码/license/commit/diff/build）与artifacts/replays/n10-20261028-450-vins-calibrated-gyro-bias（真实输出、native trace/hash/公共时间结果）。
