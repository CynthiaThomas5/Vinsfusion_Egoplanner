# #072：fresh epoch回环漂移重复实验

**结论：位置误差降低取得部分复现，航向改善很小；本次只验证到一条真实回环，不构成可重复性、飞行或“不漂移”证明。**

## 方法与运行

本次使用与070-02相同的冻结runtime、VINS/loop_fusion二进制和在线输入，在fresh epoch `e4991d9fc740425bb45eb9bd578ff66d` 重跑七轮未武装物理支架轨迹。观察器使用`config/components/localization/loop_observer_local_revisit.json`的0.1m采样间距；默认0.2m配置、匹配/PnP逻辑及健康门未改。runtime SHA-256为`da30b333a4d5589bc20b6500ecd18c9d3a8f16211f5a42f76ad9f0ea8a062256`，与前一试次相同。在线真值没有输入回环后端，后端不发布控制或TF。

轨迹探针完成47/47阶段。回环后端报告94关键帧、43候选、1条验证边和1次优化。边0→57的源时间分别为105.964s和551.332s，相距445.368s；独立Gazebo IMU几何核验的闭环平移误差3.14cm、旋转误差0.278°。raw→corrected位姿变换约在闭环关键帧后0.200s出现，测得平移变化5.03cm、旋转变化0.018°。回环专用13项核验全部为true。

只在初始静止段用一个位姿将raw VINS对齐到独立Gazebo IMU真值，尺度固定1；同一变换应用于raw和loop corrected，闭环后不再对齐。按照精确源时间戳配对，共5,093对样本，覆盖744.348仿真秒，raw覆盖率100%，真值插值最大括距20ms。真值仅用于离线评估。首条验证边之前两条输出的位姿坐标重合。

## 误差结果

| 区间 | raw位置RMSE | 回环修正位置RMSE | 位置下降 | raw yaw RMSE | 修正yaw RMSE | yaw下降 |
|---|---:|---:|---:|---:|---:|---:|
| 全共同区间，744.348s | 5.930cm | 4.273cm | 27.94% | 0.7650° | 0.7561° | 1.16% |
| 首次修正后至记录结束 | 8.383cm | 4.705cm | 43.87% | 1.0869° | 1.0690° | 1.64% |
| 第7轮返航驻留最后10秒 | 10.791cm | 7.153cm | 33.71% | 1.2858° | 1.2678° | 1.40% |

按时间加权的全程位置RMSE为5.888→4.265cm；该算法排除采样间隔超过200ms的区间，支持时长703.948秒（全区间的94.57%）。样本RMSE与按时间加权RMSE是不同统计量。位置误差降低明显，但仍有约7.15cm的第7轮返航残差；yaw改善有限，残留约1.27°。

070-02先前同轨迹观测到2条验证回环、2次图优化；072只观察到1条、1次。因此，本次只支持“fresh epoch中出现一条有效回环并降低本记录位置误差”，不支持回环数量、修正幅度或长期效果已经稳定复现。

## 收尾、核验与限制

fixture探针的最终结果为`failed`，原因为“detached fixture removal was not acknowledged”。该FAIL完整保留。独立停机前PX4 VehicleStatus为`arming_state=1`（DISARMED）；记录中附件状态包含`detached`且`fixture_may_remain_attached=false`；停机前Gazebo模型清单显示0个模型。loop backend退出码为0。`project.sh stop`退出0；之后只剩两个与本项目无关的容器运行：`volant-height-route-probe`和`natfrp-service`。

报告的8个输入哈希均复核一致；分析脚本SHA-256为`a4d4aa130baa2aac0d098e5dc3f979b9ac175d48c296eda5003591e71cd886e3`，模型SDF哈希一致。CSV有5,093行，独立重算raw/corrected位置与yaw RMSE均与机器报告逐位相同。误差图由单独的主机绘图脚本生成。容器中的完整分析进程写完JSON/CSV后因可选matplotlib不可用而未能完成绘图；主机完整重跑又无法覆盖容器生成的root-owned JSON/CSV，错误保存在run目录的`loop-drift-comparison.log`。所以不声称该完整命令退出0。

这是一次理想仿真、未武装支架的局部重复路线；无自由飞行或真实设备证据。回环结果未接入导航/PX4。没有修改项目生产代码或门限，故不运行构建／软件回归。离线比较文件位于`artifacts/runs/real-loop-20261022-072-01/`；关键输入、输出与算法报告SHA-256见同目录`loop-drift-comparison.json`。
