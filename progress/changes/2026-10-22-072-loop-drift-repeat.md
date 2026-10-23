# #072 第4个小目标：复跑回环漂移比较

[授权与约束](../../collaboration/dialogues/2026-10-22-072-loop-drift-repeat.md)。使用fresh epoch复跑070-02的未武装七轮物理支架仿真，观察真实回环并离线比较raw VINS和独立loop_fusion输出。没有修改生产代码、默认配置、健康门、控制链路或第三方源码；实验前已有未提交改动均保留。

## 结果

- runtime、二进制和冻结在线输入与070-02一致；使用局部复访观察配置`minimum_distance_m=0.1`，默认0.2m与匹配/PnP/健康门未改。
- fresh epoch为`e4991d9fc740425bb45eb9bd578ff66d`。路线47/47阶段完成；loop observer记录94个关键帧、43个候选、1条验证回环、1次图优化。边0→57，间隔445.368仿真秒；独立几何误差3.14cm／0.278°。图优化约束对应的raw→corrected位姿变化在边关键帧后0.200秒出现，平移变化5.03cm。
- 用初始静止段单个原始VINS位姿对独立Gazebo IMU真值做刚体对齐，尺度1；同一变换用于两条轨迹，没有回环后重对齐。精确源时间配对5,093帧、覆盖744.348仿真秒，原始流覆盖率100%，真值最大插值括距20ms。首条验证回环前，两路位姿坐标重合。
- 全共同区间样本位置RMSE由5.930cm降至4.273cm（27.94%）；yaw RMSE由0.7650°降至0.7561°（1.16%）。首次修正后区间位置RMSE由8.383cm降至4.705cm（43.87%），yaw由1.0869°降至1.0690°（1.64%）。第7轮返航最后10秒位置RMSE由10.791cm降至7.153cm（33.71%），yaw由1.2858°降至1.2678°（1.40%）。修正后仍有位置／yaw误差，不支持“无漂移”。
- 与070-02相比，前一轮有2条验证回环和2次优化，本轮只有1条和1次；因此只确认该fresh epoch中位置误差下降方向再次出现，不能称回环次数或效果稳定复现。

## 验证与收尾

- `real-loop-evaluation.json`中的13项回环子检查均为true；其`small_goal_2_passed=true`只代表回环验证子目标，不覆盖fixture探针结果。
- fixture探针以`failed`结束，原因是detach RPC未获确认。保留原始FAIL；独立停机前PX4状态为`arming_state=1`（DISARMED），fixture结果含attached与detached状态且`fixture_may_remain_attached=false`，停机前Gazebo清单显示0个模型。loop backend退出码0。
- `bash tools/project.sh stop real-loop-20261022-072-01`退出0。随后`docker ps`只见`volant-height-route-probe`和`natfrp-service`两个无关容器仍在运行。
- 机器报告中列出的8个输入SHA-256、分析脚本和模型SDF哈希均与文件一致；CSV有5,093行，独立重算四条位置／yaw RMSE列与报告一致。误差图由`plot_loop_drift.py`独立生成。
- 完整比较脚本在容器内写出JSON/CSV后因缺少可选matplotlib而未能由同一进程画图；主机侧尝试直接重跑时因容器创建的root-owned输出文件不可覆盖而失败，原`loop-drift-comparison.log`保留PermissionError。分离绘图已成功；不把完整比较命令报告为退出0。
- 这是数据采集与离线分析，无生产代码修改；未运行构建或软件回归。`git diff --check`在收尾执行。正式里程碑不升级。

原始数据、报告、图与哈希见[轻量验收报告](../evidence/loop-drift-repeat-20261022-072.md)及`artifacts/runs/real-loop-20261022-072-01/`。下一步建议只读审计为何本轮43个候选最终仅1条验证回环；须用户批准后开始。
