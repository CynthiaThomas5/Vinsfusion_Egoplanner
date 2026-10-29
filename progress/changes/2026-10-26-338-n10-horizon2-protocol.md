# #338 N10.3 局部时域对照协议

根据 #337 的最终动力学可行性拒绝，预声明单变量对照：保持 16 m 任务、0.10 m/s 每轴速度、0.25 m/s² 加速度和其余运行输入，规划 horizon 从 5 m 改为 2 m。只有完整目标、3 sim-s 到达、600 sim-s active hold、独立误差/速度/地图指标及安全落地都满足，才支持该候选。

验证：profile/协议 JSON、runner Python 编译、runtime 脚本 Bash 语法通过；该静态检查不产生运行结果。

证据：[采样前协议](../evidence/n10-independent-calibration-protocol-20261026-338.md)。
