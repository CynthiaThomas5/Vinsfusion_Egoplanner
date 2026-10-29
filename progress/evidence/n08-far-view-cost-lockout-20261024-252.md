# N08 #252：新增远端上视之前的定位质量拒绝

扫描完成4阶段，原有第5阶段pitch=+0.45附近触发normalized_cost_exceeded=1.169787。未执行新增远端顶板观察，不能评价该观测假设。没有after/post-release地图、曲线或制动数据。fixture自动安全清理确认脱离／不存在，独立读回DISARMED/landed、bridge disabled、零控制样本；容器安全停止Exited(0)。

下一#253只缩小远端上下视pitch到±0.1rad，其他速度／地图／health门保留；根据远端与原点2.4m距离、顶部／地面与相机约1.35m高度差，在相机垂直视场基础上采用小俯仰覆盖上下表面，减少旋转造成的特征残差。
