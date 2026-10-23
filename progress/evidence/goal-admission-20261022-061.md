# #061 离线目标准入与名义净空审查

**本轮离线审查完成；在线目标准入缺口尚未修复，未启动仿真或飞行。** 旧4m复访配置保持禁用，没有生成或启用替代飞行配置。[机器报告](goal-admission-20261022-061.json)。

## 为什么危险目标会被接受

审查了#060两轮实际转发的目标及对应源码；自有导航节点源码哈希与该轮运行指纹一致。

1. `uav_navigation/node.py:_goal_request`检查定位、epoch、frame、位姿／容差数字合法性、里程计新鲜度和EGO订阅端存在，但不查询目标体素／机体邻域。`_execute_goal_impl`复核上下文并发出目标，`task_state.py:submit`也只有任务身份和状态策略。
2. EGO `navigationGoalCallback`将有限值、同epoch目标入队；`planNextWaypoint → planGlobalTraj`生成全局参考多项式，该成功返回不是目标可达或碰撞证书。局部避障不能代替入口拒绝不可达终点。
3. `grid_map.h:getInflateOccupancy`读取inflation mask，raw unknown独立存储；初始化时raw全unknown而inflation为0，所以这一查询不天然拒绝unknown。部分局部范围外体素会恢复为unknown，不能把旧“看过”当作当前仍有可用free证据。
4. 当前rebound／refine和FSM安全检查含前2/3截断逻辑，没有据此得到一次全活动曲线与完整机体的统一安全证书。

这确认了准入与安全语义的缺口；**不证明第3／4项就是#060净空失败的确切原因。** 旧任务记录器只保存规划消息、位姿和占据点数量，没有保存目标时刻原始free／unknown／occupied体素。不能从点云计数或SDF反推当时在线地图把4m目标标作occupied还是unknown。具体源码路径、行号、哈希和实际转发goal_id见`061-checks/source-admission-audit.json`。

## 两份实际记录上的静态几何复核

使用每轮保存的实际`vio_initialization.sdf`并核对`world.json`哈希，沿用原始VINS单一起飞前SE(3)对齐、尺度1和同一起飞后odom原点。机体为IMU中心、覆盖全部姿态／旋翼角的标称球，半径约0.48194m；只检查非地面静态碰撞体，没有校准定位／跟踪／制动误差预算。

候选只存在于离线报告，数值均为**目标偏移而非返程路程**：13m偏移表示从16m处返回3m。

| 目标偏移 | 端点名义球余量范围 | 假设16m处直连该点的连续余量下界 | 结论 |
| --- | --- | --- | --- |
| 旧4m | −0.687～−0.683m | −0.697～−0.693m | 目标点在柱体内，继续禁用 |
| 旧8m | +0.318～+0.360m | −0.523～−0.507m | 端点空旷不代表直线路径可行 |
| 候选6m | +1.312m | −0.523～−0.507m | 端点虽空旷，直连仍穿过其他柱体 |
| 候选13m | +1.599～+1.603m | +1.339m | 可作为后续短返程诊断的静态候选，未批准飞行 |

13m候选点向下至起飞前对齐原点高度的固定XY、非地面球形列检查下界为+1.589～+1.593m。此列只是几何假设，不代表实际故障降落会沿该列、处理地面接触或满足漂移／制动预算。

![旧目标与候选目标的标称球形包络](../../artifacts/runs/goal-admission-20261022-061-checks/goals-01.png)

直线检查包含端点，最大采样间距0.02m；利用各box／cylinder有符号距离及其最小值的1-Lipschitz性质，从最小采样净空再减去半个实际间距，得到连续标称下界。薄障碍跨在两个采样点之间的负例也会拒绝。**这不是对实际B-spline或实际飞行的扫掠验收，更不是在线已知free地图的证明。**

13m短返程仅适合将来先验证目标准入／短动作安全；固定回环后端查询排除最近50关键帧，这样的短往返不自动满足真实回环验证条件，不能为了触发回环修改门槛。

## 工具与验证

- `tools/debug_truth/audit_navigation_goals.py`：只读实际run、世界与对齐，分别输出目标球、非地面垂直列和直线走廊；始终明确`flight_admissible=false`，不会输出启用的飞行配置，也不发布ROS消息。
- `tools/debug_truth/world_geometry.py`：复用box／cylinder距离与组合姿态，拒绝未支持的include、相对frame、动态模型、未知碰撞几何；只允许显式原点水平ground_plane被省略。
- `evaluate_clearance.py`共享上述基础距离函数；#058-04、#060-01、#060-02三份真实记录重算的完整净空JSON与原报告完全一致，未修改旧原始记录／旧结论。
- 新增7项边界测试，最终全套**175项回归＋真实ROS action／250Hz时钟集成通过**，最大pose接收年龄约0.054s。真实审计CLI拒绝布尔伪数字目标偏移且不生成成功报告。
- 本轮没有修改ROS节点、第三方算法、健康阈值、控制出口、地图配置或禁用配置；未重新编译ROS，也没有SITL／实机飞行通过证据。静态与回放不能替代它们。

复算命令（第二份记录同理）：

```bash
python3 tools/debug_truth/audit_navigation_goals.py \
  artifacts/runs/vio-residual-20261022-060-01 \
  --candidate-offset 6,0,0 --candidate-offset 13,0,0 \
  --output artifacts/runs/goal-admission-20261022-061-checks/goals-01.json --plot
```

下一小步建议补在线地图的只读目标／机体邻域查询，绑定当前epoch、map_id和融合新鲜度，并在目标转发前对occupied、unknown、地图外或无法查询明确拒绝。先做隔离接口验证，不解锁、不飞行；即使入口门通过，完整轨迹／失效降落安全仍是恢复飞行前的独立前提。
