# #499 N12 RPE固定输入诊断进行中

关联对话：[#499](../../collaboration/dialogues/2026-10-29-499-n12-vio-fixed-input.md)。

#498正常完成与安全停止后归档，固定合同RPE FAIL，驻留/绕障/净空等通过。新增#498失败证据和逐时段分析。隔离复制当前vendor数值源码，仅复用#449可靠回放输入QoS与可选native trace；estimator.cpp与当前生产源码SHA相同，GPL和来源记录保存。真实vins构建47.6秒成功，有已有弃用类型编译warning。生产运行源码/参数/安装未改。

产物artifacts/n12-prepared/n12-20261029-499-fixed-input及artifacts/replays/n12-20261029-499-fixed-input。baseline498正在独立ROS_DOMAIN186、network none容器重放；预期原bag包含30885IMU、左右各3744帧，需核对实际native callbacks和全部processed pairs，再解释数值。当前未取得回放结论，N12仍0/3。下一完成baseline输入审计、同源时间RPE分解并选择证据驱动动作。Goal保持active。

## 基线已完成

30885IMU/3744对双目的native回调与processed全部完整，无catch-up丢帧。原RPE P95=0.059407374m，完整回放0.059407589m，失败复现。高误差段主要为位移估计误差，139/151求解NO_CONVERGENCE且solve P95约23.7ms。下一唯一变量max_num_iterations8→16、40ms时间预算固定；离线iterations16_498已启动，生产参数未改。详见progress/evidence/n12-fixed-input-baseline-20261029-499.md。
