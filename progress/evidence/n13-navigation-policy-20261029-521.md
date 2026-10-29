# #521 N13功能验收策略验证

本轮目标：按用户批准设置N13，普通有界模式，完成配置/离线评估修改与验证，无飞行。N13仍not_started，正式0次。

当前[revision13配置](../../config/acceptance_n13.json)将十类独立VIO/地图/时序/跟踪/密集几何/资源队列指标改为诊断，原参考数值保留在diagnostic_reference字段。真实多障碍绕行、地图观测/更新、替换轨迹实际执行、到达、零违规碰撞、正常落地上锁/控制归零及核心证据仍必须满足。原生PX4/EGO行为和当前速度/加速度/yaw/膨胀参数未变；故障注入和旧动态箱体ACK不是新增前置。

接触/终态直接重算原始接触传感器、模型清单、分段时间线、动作记录和独立PX4/桥接终态，绑定goal/epoch身份；缺核心输入判不足，实际碰撞/动作失败/异常终态判失败。密集物理步和区间界放入诊断。旧[revision12](../../config/history/acceptance_n13_revision12.json)与历史N12配置/报告保留。N13场景/协议明确pending，整体不能因核心项支持就通过或计数。

验证命令与结果：

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.test_n13_navigation_policy tools.test_n13_clearance_policy tools.test_n10_acceptance tools.test_n10_replan_reference tools.test_n12_rpe_policy tools.test_n12_surface_policy`：84项PASS（15新、69历史兼容）。
- `PYTHONPYCACHEPREFIX=/tmp/n13-521-pycache python3 -m py_compile tools/n13_navigation_policy.py tools/debug_truth/evaluate_n10_acceptance.py tools/test_n13_navigation_policy.py tools/test_n13_clearance_policy.py`：PASS。
- 公共评估器evaluate，以revision13分别只读复放#518/#512评估视图及n11-run-metrics.json：运行身份、核心输入哈希、到达参考点PASS；到达、原始接触/正常终态、核心观察器身份PASS。整体均INSUFFICIENT（N13场景协议pending）；#512速度仍诊断FAIL，未覆盖旧FAIL报告。
- `python3 tools/project_status.py`：结构PASS（历史可选artifact缺链提示80，不是本轮运行失败）。`git diff --check`：PASS，具体日志保存在下述目录。

产物：[测试/复放/哈希目录](../../artifacts/runs/n13-20261029-521-acceptance-policy)、[当前规则](../../docs/n13-project-restrictions.md)、[修改记录](../changes/2026-10-29-521-n13-navigation-policy.md)。未运行ROS/PX4构建、SITL或实机；这些结果仅为离线策略验证，不替代飞行证据。没有新建运行会话或部署离线VINS候选。

未解项：N13.1的实际错位多障碍场景和地图/重规划/基本路径证据协议尚待实现、绑定和资格验证；历史漂移/分类/队列现象未声称修复。停止原因：本轮设置完成。唯一下一步：N13.1协议准备，随后按用户要求可见GUI正式运行。
