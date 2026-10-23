# #068 只读先验与静止／运动对照

[本轮对话摘要](../../collaboration/dialogues/2026-10-22-068-prior-controlled-observation.md)。保留既有未提交修改，不提交／推送或修改Nano。配置、src/own及已安装控制代码保持本轮开始时版本；校验见证据。

预期：区分当前先验残差中线性化基准r0与本帧Jdx项，同时验证窗口观测是否能还原视觉因子数量。再用等时长静止对照检验仅经过时间是否足以产生同类先验增长。只读诊断不是求解干预，独立初始化／估计器年龄与运动负载不完全相同，不能当严格因果证明。

文件及行为：

- VINS `0018-prior-readonly-diagnostics.patch`在0017后，锁定72023bc5d2abb14faa4c02a5c040d84f996b587a、GPL-3.0；sources.json记录顺序、补丁和源文件SHA256。仅在已有分组诊断中记录求解后／下一先验构建前的r0、当前残差、Jdx、交叉项及谱摘要，附窗口特征身份／跨度。最多1024条并标记截断。未改变因子、鲁棒核、求解、健康门、时戳或控制发布者。
- `tools/debug_truth/evaluate_prior_diagnostics.py`验证总分组、先验平方范数恒等式和视觉分量数。截断帧只能检验视觉数量下界，不能伪称完整核对；测试包含这一区别。
- `tools/debug_truth/record_fixture_truth.py`仅订阅Gazebo源戳真值，独立输出；`evaluate_fixture_odometry.py`复用已有时间插值与模型外参，静止首段单姿态对齐、尺度1，拒绝非单调／过期anchor，不生成假flight.json。增加truth终止marker选项供静止对照使用。首轮recorder启动后才补了关闭回调保护，首轮进程未加载该小改动；静止轮使用最终记录器。
- `tools/probe_prior_idle.py`只读观察200仿真秒，逐步要求同epoch、新鲜健康和DISARMED，无支架／目标／控制。192项回归包含5项新增先验和独立对齐回归；说明补入contracts/running及补丁README。

验证与运行结论详见[机器证据](../evidence/vio-prior-20261022-068.json)和[解释报告](../evidence/vio-prior-20261022-068.md)。原始日志／输入／图在artifacts/runs/vio-prior-20261022-068-{checks,01,idle-01}，build日志保留既有VLA编译告警。17包构建、222文件fresh fetch逐字节一致；静态／离线与未武装SITL分别记录，不替代飞行。

运动轮流程FAIL：完整运动及脱离后，Gazebo移除确认失败；实际模型列表已无支架，但不能把无确认覆写为成功。工具原始失败结果保留；live DISARMED后停止会话。运动／静止对照不解锁，不执行EGO候选，不证明起飞、净空、失效降落、回环或Nano资格。P4–P6和S1–S6状态不变。

下一步应围绕先验形成过程选择一项诊断或干预，再复现；本轮不支持放宽门、忽略先验或清锁续飞，也不能用不越线的支架／静止观测解释旧059与060的所有触发。
