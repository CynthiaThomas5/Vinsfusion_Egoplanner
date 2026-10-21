# GOAL B/C/F 五步膨胀与地图下界复测 #252–#254

关联对话：[2026-10-20-028](../../collaboration/dialogues/2026-10-20-028-goal-f-inflation-ground-boundary-followup.md)。

本组运行未改自维护源码、第三方源码、项目配置或 canonical launch 默认值。#252 使用 run-local `obstacles_inflation=0.5 m`、0.1 m分辨率与 `flight_type=1`，测得峰值膨胀云17,255点，同stamp原占据1,113点（15.50倍）；定位于40.933墙秒以 `normalized_cost_exceeded` 锁定。

#253 将运行期 `ground_height` 设为−0.05 m但沿用原观察启动顺序。定位适配器在主探针启动前已报 `propagated_stale`；主窗口内有988帧深度，优化里程计转发、EGO深度／位姿配对、原占据和膨胀占据均为0。探针因这些前置条件缺失以退出码1结束，因此该轮排除出边界比较。raw VINS 仍有优化和传播输出，不能把该现象归因于地图高度。

#254 将只读探针提前到运动开始前，使用同一场景、五步膨胀和−0.05 m地图下界。定位有效至46.067墙秒，随后以 `normalized_cost_exceeded` 锁定。锁定前相机高度采样范围−0.0039至0.1299 m，相对−0.05 m下界处于图内，EGO日志的最后同步输入 `last_sync_in_map=1`；探针收到1,000组深度／位姿并采到最多1,288点原始占据。峰值膨胀云18,027点，同stamp原占据1,262点（14.28倍）。EGO另有24条输入超时日志、分属两组同步停顿，故不证明持续建图。离线固定尺度SE(3)评估位置RMSE为8.09 mm；箱体表面残差中位数/P95为2.00 mm/2.86 cm，圆柱为7.28 cm/14.90 cm（57.1%点在10 cm内）。几何数据受定位锁定影响，仅作描述。

没有发布导航目标，没有规划成功或轨迹，未启动 PX4／控制器；没有测量碰撞、自由／未知空间、最小机体间距、跟踪或制动。膨胀点数不是规划安全证明或纯计算成本倍率。参数保持 run-local；GOAL B/C/F 与 P2状态不变。详见[汇总证据](../evidence/p2-ego-inflation-ground-boundary-20261020-253-254.json)、[#252膨胀profile](../evidence/p2-ego-inflation-profile-20261020-252.json)。

验证：#252 与 #254 容器退出码0；#253 按观察器前置门失败退出码1并分类为无定位转发的排除轮。两个边界场景均通过 `gz sdf -k` 并报告 `Valid`（输出保留 `gz_frame_id` schema warning）；#254 离线 evaluator、run-local shell语法和Python语法通过。`python3 tools/project_status.py` 为 PASS；相关报告的原始／源码 SHA-256 审计309/309通过；JSON解析、`git diff --check && git diff --cached --check`、run-local `bash -n` 与 `py_compile` 均通过。#252／#254容器退出码0，#253按定位前置门失败并排除；两个边界world的 `gz sdf -k` 均报告 `Valid`（保留现有 `gz_frame_id` schema warnings）。本轮无项目源码或配置变化，不重复 colcon 构建。

下一步在健康门不变的前提下追踪 EGO 输入／地图更新间隙，随后在开放走廊测试无控制器的 EGO 目标规划；补足圆柱覆盖并取得真实轨迹与机体距离数据后，再评估 GOAL F阈值冻结。
