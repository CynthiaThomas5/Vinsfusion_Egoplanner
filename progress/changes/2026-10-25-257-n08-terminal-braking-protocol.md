# #257–#258 限定末端制动测量协议

用户范围与决定见[对话摘要](../../collaboration/dialogues/2026-10-25-255-n08-callback-coherence.md)。本项依赖#251速度最终检查、#255回调一致性修复与#257新鲜运行曲线证据；N08父目标不因此通过。

新增N08专用执行器 `tools/run_n08_braking_trial.py`、纯几何工具 `tools/n08_trial_gate.py`、离线独立评估器 `tools/debug_truth/evaluate_n08_braking.py` 和相应测试，配置在 `config/components/navigation/n08_forward_braking_trial_goal.json`。mission_runtime仅为该指定配置开放native execute；泛用execute继续拒绝。bridge独占控制，不增加控制发布者。

试验依据：EGO max_vel逐轴0.10m/s、参考向量上限0.12m/s，由#251实际归档样条的C++复算和最终可行性guard支持；参考加速度0.25m/s²。真实速度由位置环决定，不能将参数值当实际限速。历史相同PX4位置控制的低速终段跟踪最大误差0.1291／0.1385／0.1435m仅作有限先验，当前在线误差退出线0.15m、完整机体外额外净空0.25m，真实水平速度退出线0.15m/s。

在当前已观测区域内，前方0.6m目标曲线以零末端速度／加速度收尾，随后保持3秒，沿同一走廊返回原N05 pad再降落。当前raw快照连续capsule必须全free；预enable home-pad N05与离线回读必须通过，空中实际起点重新检查capsule。无需把尚未证明的任意移动位置降落当已通过；正常降落限定原起降点。

在线检查包括epoch／定位／时钟、唯一发布者、实时样条控制凸包／导数速度界、参考速度、实际水平速度、跟踪误差和运动范围；异常经现有bridge取消／Land并记录真实终态。真值观察器只读，执行器不订阅真值。离线评估采用唯一pre-enable SE(3)、无缩放；报告实际速度、减速距离、响应延迟、停车保持、跟踪误差和有限样本减速度。0.22秒对称平滑限制响应时延精度，不将分位值称为保证减速度。

静态：bash -n通过，Python语法通过；22项N08相关单元通过，独立制动4项解析／断流／回退检查通过。真实ROS TrialProbe 5项通过，mission配置准入在当前launch记录上通过。日志：`artifacts/runs/n08-20261025-255-localization-callback-coherence/trial-probe-updated-tests.log`、`mission-trial-gate.log`。#257运行进行中，运行通过状态待实证写回。
