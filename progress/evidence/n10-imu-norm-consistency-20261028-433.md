# N10.3/#433 碰撞后四元数范数的IMU短窗一致性重算

## 结果

从#428已关闭的MCAP用原始header stamp提取133.700–133.812秒29条相机IMU，不重建/补造输入。最后一个optimized quaternion源戳133.752秒、范数1.0，至故障对应IMU源戳133.808秒共14个4ms间隔（56ms）。原故障header戳133.807999999ns与IMU端点差1ns，报告同时保留两戳并显式声明匹配容差，未改原记录。

按源码fastPredictIMU的midpoint gyro与未归一化deltaQ乘积，零gyro bias近似重算结果：

- 预测范数1.0119565061365674；原故障范数1.0119563044024111，差约2.02e-7。
- 四元数方向差1.94276e-5 rad（约0.00111度）。
- 若日志所示gyro bias模0.0003514308 rad/s在14步内不变，允许任意方向的条件范数区间[1.0119561839234084,1.011956828356793]，原值在其内。
- 每步将增量规范化的数学反事实范数约0.9999999999999997；此反事实未部署。

乘法范数递推为 ||q_next||=||q||sqrt(1+||midpoint_gyro-Bg||² dt²/4)。这为碰撞后大角速度时的范数增长提供了与原始输入/源码高度一致的数值解释，不是无效零四元数或简单字段编码错误的证据。它不是完整VINS/Ceres重放；实际bias向量方向和内部每次状态更新没有录全，条件区间不能提升为无条件证明。

## 与首次碰撞的关系

首次contact132.168秒比该范数故障早1.640秒。无论输出归一化是否改善范数，均不能消除更早的轨迹/地图错误，也不能将翻覆后的估计视为可继续导航。没有修改VINS、适配器阈值或继续飞行策略。本项只关闭短窗数值机制审查，父N10.3不通过。

## 来源与可复算产物

artifacts/n10-prepared/n10-20261028-433-imu-norm-replay/包含extract_imu.py、extract.log、imu-window.json、replay.py、norm-replay.json。

提取在固定ROS镜像内network=none、主工程只读挂载运行，rosbag2_py seek/filter后读取377条消息取得29条源窗数据。重算使用python3 .../replay.py。数据戳间隔与端点均assert检查。

MCAP、metadata、raw odometry和故障日志SHA已保存。直接验证dependencies/sources.json SHA及VINS二进制与运行合同一致；patched estimator.cpp SHA与锁定manifest一致。Utility header没有单文件hash条目，记录当前源码审计hash，不宣称它有独立运行合同hash。第一次试图按runtime.files直接索引estimator.cpp遇KeyError，发现该合同通过dependencies manifest而非逐vendor文件锁定；改为验证真实锁定链，未添加虚假的直接hash。

脚本最初执行得到重算数值后，补入完整MCAP/源/二进制来源hash；没有据此更改数值。当前#428收尾状态未变化，未使用紧急disarm。
