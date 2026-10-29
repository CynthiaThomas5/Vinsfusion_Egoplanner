# #260：真实前向末端制动已测，返航拒绝，整轮未通过

**结论：不是速度门卡住。** EGO原生execute已实际执行前方0.6m目标，到达及保持成功；独立制动数据有效。返航action被当时raw map的`map_query_unknown`拒绝，因此native trial=FAIL、独立总评passed=false、N08仍in_progress。未修改unknown规则或用起飞前旧图替代当时的图。

## 试验与版本

配置逐轴max_vel0.10m/s、max_acc0.25m/s²、独立参考向量门0.12m/s；桥位置控制，不把配置值当真实机速。复用0044最终样条动力学检查、#255回调一致性修复和#259快照限时等待。当前run原N05 pad准入、连续body+0.25m走廊、空中实际起点capsule均通过；地面／空中快照各5次请求后accepted=ok。唯一桥控制发布者，执行器不订阅truth。

15阶段扫描完成并支架移除。助手因旧DISARMED样本给出清理告警；随后独立5秒读回DISARMED、landed、bridge DISABLED、控制0，`n05-monitor-resolved.json`保留解除证据。preflight／当前N05在线离线检查通过后才enable。前向action succeeded，停车保持后返航被拒，经原bridge disable/Land在前向终点附近实际落地上锁；正常返回原pad未完成，不能继承原pad的降落几何资格。

## 独立测量

以唯一PRESTREAM前SE(3)、scale1对齐；truth只读，20ms采样网格、0.22秒对称速度平滑。全部源时序保留，不排序／重写时间。参考记录有123条相同源戳且position/velocity/acceleration完全相同的重复发布，计数后仅取同一源状态一次；0次倒退、0次同戳矛盾。最初分析器对此重复格式拒绝；分析器扩展后增加精确重复、矛盾重复和参考倒退测试，运行控制与验收阈值未变。运行时分析器hash与离线分析器hash分别保存在机器报告，原始记录不改。

| 指标 | 测量 |
|---|---:|
| EGO参考峰值向量速度 |0.08067675m/s|
| 实际水平／三维峰值速度 |0.08144609／0.08182327m/s|
| 独立水平净位移 |0.60321569m|
| 从规定参考减速起点至阈值停车的距离 |0.30233908m|
| 该段持续时间 |4.712s|
| 达到持续减速判据的时差 |1.412s|
| 观测减速度p10／均值 |0.01313737／0.01624347m/s²|
| 最大参考跟踪误差 |0.08362936m|
| 阈值停车1秒内水平位置变化 |0.01972740m|

“停车”判据为水平速度≤0.03m/s、垂直≤0.05m/s持续1秒，不能解释为精确零速。参考减速起点是在参考峰值后沿目标方向acceleration<−0.005m/s²；实际响应判据为减速度≥0.005m/s²持续0.15秒。因此1.412秒包含控制动态／判据／平滑影响，不是纯通信延迟。分位减速度仅为这一有限样本，不能作为任意取消制动或硬件的保证下界。

10项核心运动测量检查通过；走廊、live样条、定位连续、唯一控制、时钟、watchdog和落地检查通过；**native_trial_completed与returned_to_n05_home_pad两项未通过**。全飞行VIO位置RMSE0.005184m、最大0.011935m、invalid状态0。返航unknown的具体空间成因尚未确认，不能擅自解释为视野问题或降低unknown门。

## 验证、产物与交接

`D435I_N08_MODE=execute ... project.sh mission ...n08_forward_braking_trial_goal.json`退出1，保留失败。`python3 tools/debug_truth/evaluate_odometry.py RUN`成功；`evaluate_n08_braking.py RUN --plot`生成指标与图，因返航失败退出1。N08相关25项单元、ROS快照6项、ROS回调一致性6项及TrialProbe5项通过；#255已有17包构建证据，不把单元或构建当飞行通过。

原始数据、[速度图](../../artifacts/runs/n08-20261025-260-terminal-braking-measurement/n08-braking-speed.png)、样条／两张raw map／源时间线及独立报告在 `artifacts/runs/n08-20261025-260-terminal-braking-measurement/`；[轻量JSON](n08-terminal-braking-measurement-20261025-260.json)保存指标和输入哈希。最终新鲜5秒读回landed/disarmed、bridge LANDED、控制0、fixture absent，安全停止Exited0。

停止原因：完成用户指定“取得实际制动测量后报告”的数据与部分结论交付；整轮试验未满足原返回标准，明确保留失败，不将N08通过。下一唯一子项#261为返航raw unknown的证据审计／修复；先用现有记录，不盲目重扫。之后仍需运动中取消制动、至少3次独立冷启动重复和N05/N06预算回填。已通过N07不复测。
