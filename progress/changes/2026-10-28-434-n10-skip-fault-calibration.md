# N10-SCOPE-20261028-434：按用户要求跳过故障校准

## 用户决定与范围

用户明确要求“我的工作不需要我考虑故障之后的校准，直接跳过这一部”。当前Goal为N10.3，本轮按排除N10.3故障注入和故障后处置量测执行。既有失败/不足不改成通过；不据此声称GOAL E/N15已验收。正常导航的零碰撞、定位/地图/跟踪/全机净空、重规划和资源/队列标准继续推进。此处是经用户授权的范围变更，不是原标准下通过。

## #428取消与清理

核对docker label和Cmd确认当前对象仅为本项目SITL仿真容器，Cmd为tools/sim_runtime.sh，保存末态到n10-user-cancelled-fault-calibration.json，然后按取消当前实验受控docker stop -t30，exit0，确认State.Running=false。没有发送PX4紧急disarm或其他飞行控制。取消时仍armed/LANDING、landed=false，故障终态未验证，原safe-to-stop=false和flight FAIL保留。监护进程观察到容器结束后自行exit0，不再等待事故后自然落地。

## 实际修改

- GOAL.md、N10执行计划及remaining-small-goals加入用户范围覆盖说明。
- acceptance revision4将fault_exit_to_terminal_px4_state设required=false并记录用户决定；数值阈值不改、配置仍draft。
- 离线evaluator汇总只对当前required指标判断数据覆盖，所有原指标及状态仍输出；直接安全/任务失败依旧FAIL，draft或无required有效结果仍不能PASS。
- 新增4项测试，连同原23项共27项通过。第一次编辑按不存在的criteria配置键访问被KeyError拒绝，未写配置；核对真实metrics键后修正。此修改不影响runtime控制。

## 验证与交接

PYTHONPATH=tools python3 -m unittest tools.test_n10_acceptance -q：27项通过。随后运行语法、project_status与git diff --check。无新飞行，#428容器停止及monitor退出均已核验。

下一项#435：将已在隔离真实plan_env包通过10项检查的halo/索引修复纳入固定第三方补丁链，构建并只验证正常导航。当前故障校准步骤被跳过，N10.3整体未完成。
