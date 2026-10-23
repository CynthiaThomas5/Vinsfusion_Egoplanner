# #060 分组诊断、失败试验与无效路线禁用

对应[对话摘要](../../collaboration/dialogues/2026-10-22-060-residual-validation.md)，完整结果见[证据](../evidence/vio-residual-20261022-060.md)。两轮飞行FAIL，无里程碑升级。

## 改动

- `dependencies/patches/vins/0017-continuous-cost-diagnostics.patch`、`sources.json`及补丁README：固定上游和0016后的只读连续分组Evaluate选项，记录其耗时；原默认首次越界模式保留。未改求解因子／参数或健康门。
- `tools/sim_runtime.sh`、`project.sh`：显式传递并校验诊断模式，写入每轮`vins-diagnostics.json`。
- `tools/run_vio_ego_flight.py`：保留完整源遥测，修正先前丢失分组／bias字段的记录缺口，无新图像订阅。
- `tools/debug_truth/evaluate_residual_transition.py`、`tools/test_residual_transition.py`：分组总值一致性、代价／分量数对归一化变化的分解、单次诊断缺少前一帧分组时不虚构、同源独立误差配对与图形。
- `config/components/navigation/room_loop_goal.json`：离线确认4m目标在柱体内后置enabled=false，保留历史坐标和原因。`tools/flight_profile.py`、`mission_runtime.sh`在前检和起飞前拒绝禁用配置；`test_flight_profile.py`覆盖真实禁用配置及独立三段合成fixture。默认16m演示保留。
- docs明确#059旧路线禁止继续执行；CURRENT与#059历史报告指向后续路线纠错。不修改旧原始记录或将失败补算成功。

## 验证

服务器`bash tools/project.sh build ros`17包完成；最终`bash tools/project.sh test`168项测试＋真实ROS action／250Hz时钟集成通过。完整`fetch_dependencies.py --source vins_fusion --target ...`重建222文件与唯一vendor一致。独立domain185实际flight CLI禁用配置探针返回非零且未初始化ROS／生成flight文件。最终静态、Python编译／shell语法、`project_status.py`与`git diff --check`通过。

01连续分组与02默认分组均40s前检／16m去程原生action和独立驻留通过，返程35.508／37.028仿真秒质量门锁定；总代价下降而分量数下降更多，先验占触发帧代价约90%／80%，真值诊断误差8.93／7.23cm。不能将此归因直接反套到#059原先的分子跳变。

离线核对4m目标在柱体内；01／02名义包络最小净空−0.132／−0.201m，不能算有效安全路线或证明无碰撞。两轮均任务FAIL／落地上锁，回环／优化0；后端和容器退出0。路线禁用发生在试验之后，无最终禁用配置的新飞行通过证据。

未改健康阈值、控制发布关系、Nano、其他容器；未提交／推送。下一步只做离线目标可达性／净空和先验／健康指标审计，解决这些问题前不重复旧路线飞行。
