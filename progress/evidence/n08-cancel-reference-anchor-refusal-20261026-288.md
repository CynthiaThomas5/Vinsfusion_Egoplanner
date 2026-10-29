# N08 #288：EGO取消停车重规划被0.2m近目标门拒绝

## 结论

**FAIL：**真实`caller_cancel`在目标速度窗内触发，bridge收到取消请求，但EGO未发布替换停车样条。失败原因已由现场日志确认：目标相对EGO参考起点过近，触发EGO原有固定近目标拒绝；不是地图证书拒绝。该次无制动／保持测量，不能计作N08出口通过。

## 运行前置与触发

Run：`n08-cancel-translation-prescan-20261026-288`。同一冷启动中N05支架扫描完成6/6阶段并确认夹具移除；post-release与mission current-area在线／离线入口准入通过；40.0019s只读preflight、方向性ground／airborne capsule及终点landing预检查均通过。完整资料见该run目录中的`n05-run-summary.json`、`preflight.json`、`n05-current-area/`、`n08-trial-airborne-map.json`和`n08-trial-destination-landing-pre-goal.json`。

取消窗口内PX4实际水平速度为0.0402045m/s，EGO参考速度为0.0574451m/s；位置约为`[0.001171, 0.017094, 0.875736]m`。action结果：`status=5, success=false, outcome=canceled, reason=caller_cancel`。EGO按测得速度算出0.246m停车距离。

## 根因证据

`artifacts/runs/n08-cancel-translation-prescan-20261026-288/vio.log`中取消时同戳EGO position command约为`[0.060080, 0.013381, 0.876239]m`。活动EGO参考点相对PX4实际位置前进约0.059m。原补丁把停车目标放在实际位置沿速度前进0.246m，因此目标相对规划起点只剩约0.187m。

同一日志紧接cancel记录三次`[drone 0 replan ...] Close to goal`及`refine_success=0`，随后才出现`Full-curve safety rejected: planning_failed`。EGO `reboundReplan`在`src/vendor/ego_planner/planner/plan_manage/src/planner_manager.cpp`中明确对`(start_pt - local_target_pt).norm() < 0.2`直接返回false；因此失败发生在优化和地图证书之前。`flight.json`中的`live_spline_certificates`只有原goal的traj_id=1，未观察到replacement traj_id。

## 最终安全状态与边界

运行器最终安全落地。`safety-readback/final-px4-bridge-live.json`显示bridge `LANDED`、control disabled、PX4 disarmed且landed，读回期间control mode、trajectory setpoint和vehicle command消息均为0；项目容器`Exited (0)`。原样条在planner拒绝之后继续输出，直到运行器执行安全降落；这也说明replacement stop未生成。独立制动评估因缺少停止/保持终点时间而FAIL，没有产生可用制动距离。

本次确认的故障仅定位到位置参考偏差把目标距离压过EGO原有0.2m局部门。没有放宽该门、停车距离、地图未知拒绝或其他N08验收阈值。修复是0047将停车目标锚定到取消时活动EGO参考样条位置；新SITL仍待验证。
