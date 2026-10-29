# N10.3/#438：统一离线参考、锚点与分段

完成共用评估器修复与三份归档复算，未启动飞行、未改变控制或阈值。N10/N10.3仍in_progress；不补故障校准，不计正式次数。原始归档222个已核对文件SHA全部不变。

## 实际修复

- tools/truth_reference.py从运行冻结的wrapper/camera和contact manifest绑定的base SDF核对model→IMU=[0.12,0,0.32]m；逐姿态旋转杠杆臂后转换。拒绝重复转换、未知offset/rotation及来源不匹配；不再把robot_base_frame标签当位姿原点。移除转换样本上的raw twist字段，避免暗示已做瞬时速度/坐标转换。
- 到达与raw VIO统一使用PRESTREAM前最新raw VINS样本的一次尺度1 SE(3)。#381/#385/#436的锚点、旋转、平移逐一核验完全相同，不逐段拟合或修改时间戳。速度/RPE/跟踪/地图/净空都用同一IMU点；snapshot、tracking和acceptance校验生产报告的参考/模型/转换器SHA，旧新报告混用判不足。
- 速度v2把运动、已完成请求保持和降落分别统计；无hold边界不将goal-to-landed当hold。保持按completion+completed requested duration定义，实际hold loop入口/出口未落盘的限制保留。
- 重规划几何从同一固定SE(3)将样条转到SDF world/box坐标，支持box yaw，不再使用假定spawn-relative中心；实际净空用已纠正的完整场景报告，可选point queries仍非必需。
- 物理步区间评估包络参考改为IMU。但raw Gazebo twist为机体系平滑估计，不能当瞬时端点上界；评估器现在明确输出INSUFFICIENT_INSTANTANEOUS_VELOCITY_EVIDENCE、interval_bound_verified=false。旧#403连续界不能用于最终冻结；完整求解位姿及禁止接触证据仍可复用。

## 分别复算结果

| 归档 | 联合驻留sim s | 运动RPE10平移p95 m | 保持速度误差p95 m/s | 采样全机最小净空m | 跟踪平移下界最小m |
|---|---:|---:|---:|---:|---:|
| #381 | 2.320 | 0.071179 | 0.007000 | 0.392119 | -0.253135 |
| #385 | 3.300 | 0.067890 | 0.007101 | 0.184605 | -0.422000 |
| #436 | 3.832 | 0.060495 | 0.015166 | 0.438014 | 0.205763 |

#385到达校准仍PASS；#381驻留不足仍FAIL，不倒改为通过。#436到达、raw绝对误差、map age、采样全机净空/零禁止接触、已观察表面/分类和observer identity在原草案下PASS；motion RPE10仍高于0.05m，hold速度仍高于0.01m/s，tracking标量/不确定度、动态重规划和资源/队列标准仍不足。其总体仍INSUFFICIENT。

#436跟踪平移下界负样本由旧参考下573个修正为0，最小约0.205763m。这是该版本/该场景的逐采样平移界，不覆盖地图/模型/区间运动不确定度，不用它放宽任何门限。#381/#385速度、yaw策略、模型采样率和安装身份差异在各runtime中保留，三份数据不合并为同版通过。

## 新输入核对及下一步

只读MCAP抽取#436 PRESTREAM前4秒的1001条地面IMU：加速度模均值9.8m/s²，与实际world gravity=9.8一致；实际生成VINS配置g_norm=9.80665，配置SHA已记录。确认这是物理输入不一致，尚未证明它造成剩余误差；没有修改VINS参数。下一项#439先对同一录包做仅g_norm不同的离线VINS回放，比较原阈值、时序/覆盖和分段误差，再决定修复，不通过重飞或删阈值追通过。

## 验证与产物

完整命令bash tools/project.sh test：576项单测和两个ROS集成通过。相关定向测试、py_compile通过；结构检查及git diff --check见收尾记录。只有Python离线工具/记录器元数据变化，无ROS/PX4编译产物改变，因此未执行无关重建；不是N10.5干净重建。

产物：artifacts/reanalysis/n10-20261028-438-reference-unification。各run的analysis-lineage.json、reanalysis-steps.json、n10-acceptance-evaluation-438.json及同目录原始文件完整性、重力输入审计、完整测试日志、source-snapshot与tool-freeze.json可复算。模型快照#381/#385通过原50Hz版本完整文件SHA精确恢复，不以当前250Hz模型冒充历史模型。原始artifacts/runs不改。机器报告见同名json。

来源与契约：[docs/contracts.md](../../docs/contracts.md)、[Gazebo上游OdometryPublisher源码](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/odometry_publisher/OdometryPublisher.cc)。

停止原因：#438参考修复/归档复算子项完成；父N10.3未完成。唯一下一项#439离线单变量物理输入回放。无活动飞行或需安全收尾的控制链。
