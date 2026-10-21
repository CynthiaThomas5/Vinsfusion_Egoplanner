# 当前锁定 EGO 手动目标、离线几何与健康时间线诊断 #282–#284

对应对话摘要：[2026-10-20-041](../../collaboration/dialogues/2026-10-20-041-p2-current-ego-manual-goal-diagnostic.md)。轻量证据：[p2-ego-current-vendor-manual-goal-20261020-282-284.json](../evidence/p2-ego-current-vendor-manual-goal-20261020-282-284.json)。#282–#284完整采集与文件哈希见各自 `artifacts/runs/.../run-report.json`；#284健康时间线另见 [health-timeline-analysis.json](../../artifacts/runs/p2-ego-current-vendor-goal-health-timeline-20261020-284/health-timeline-analysis.json)。

## 结果

- #282目标探针启动前定位已以`right_stale`锁定，地图清空且没有有效里程计或目标，排除为规划结果。
- #283在TRACKING、ready MapStatus（902个占据点）时发出手动目标，当前EGO发布一条匹配epoch的三阶B-spline。离线单次固定尺度SE(3)对齐使用318对样本，位置RMSE 6.64 mm、P95 11.09 mm；名义球形机体到箱体／圆柱的计算余量分别0.574/1.640 m。之后定位以`normalized_cost_exceeded`关闭地图输入，EGO进入内部`EMERGENCY_STOP`。
- #284将定位、MapStatus和VINS estimator telemetry延长采集到62.863秒。目标在6.827秒发送，定位TRACKING，MapStatus ready、921个占据点，膨胀图15,569点，EGO目标订阅者1；共捕获8条B-spline。仅对首条曲线作离线评估：310对样本固定尺度SE(3)位置RMSE 5.758 mm、P95 9.030 mm、最大10.117 mm，姿态RMSE 1.545°；相对已知箱体／圆柱的名义0.482 m球包络余量0.619/1.630 m。
- #284的545条遥测无解析错误。47.473168秒只有一条`solve_seconds=-0.544872 s`样本；该样本`solver_usable=true`、35个输入特征、22个立体特征、22条long tracks、normalized cost 0.79756。后续样本的solve时间恢复为5.657 ms；定位状态在47.508421秒以`solve_seconds_exceeded`锁定，锁定点normalized cost仍为0.79756，低于当前1.0门限。全程遥测normalized cost最大0.96617，没有越过该门限。定位质量代码对`solve_seconds<0`或超过0.1秒均返回该锁定原因；VINS telemetry patch把Ceres `Summary.total_time_in_seconds`映射为此字段。负值的底层原因未知，单轮不证明可重复性。
- #284还在更早的EGO运行阶段记录8条`odom or depth lost!`和8条`Depth Lost! EMERGENCY_STOP`日志；首条显示EGO `now=12.673`、最后occupancy更新时间11.650、同步计数130。该输入停顿明显早于之后的定位锁定，现有材料不能建立两者因果关系。
- 两轮均只运行传感器、VINS、定位/建图适配器与EGO planner。没有轨迹服务器、控制器、PX4、setpoint发布者或运行时真值输入；EGO内部FSM日志不代表实际执行。#284节点与控制话题快照中未发现控制节点或控制话题。

## 验证

- #280锁定EGO vendor overlay构建5/5包通过；#282–#284没有修改EGO、VINS、定位或建图源码。
- #284容器采集及节点/topic快照完成；首次宿主wrapper在容器完成后因尝试覆盖容器创建的root-owned几何占位文件而退出1。删除该占位文件后，宿主SciPy 1.8.0用同一离线评估器成功生成几何结果。保留的已执行wrapper哈希为`f49e0b60…ae020a7`。
- 修复#284 run-local wrapper：明确传递运行目录，宿主离线评估前移除容器生成的几何文件，并以临时文件替换runtime summary，避免所有权冲突。修复后的`run-container.sh`与`run-live.sh`均通过`bash -n`；未重新运行仿真。
- `python3 tools/project_status.py`：PASS（Structure/design check）；`bash -n` 对修复后的`run-container.sh`和`run-live.sh`均PASS；`git diff --check`与`git diff --cached --check`均PASS。自定义JSON核验确认三份run-report哈希、#284分析哈希及38个采集文件哈希匹配。上述仅为结构检查、脚本语法和证据完整性检查，不代表构建、SITL或实机验收。

## 状态与下一步

这是planner-only探索性诊断，不代表GOAL C/D/E/F通过；GOAL F净空阈值仍未冻结。保持当前fail-closed健康门和全部阈值不变。先用额外遥测/计时观测复现单次负solve_seconds值，并将原因未明的EGO输入同步停顿作为独立诊断；之后补地图free/unknown分类、覆盖与持续性证据，再冻结GOAL F并进行正式D/E验收。