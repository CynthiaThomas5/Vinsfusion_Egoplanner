# #302 负侧观察 SITL 结果

新 profile 实际到达 yaw−π/2（stage 12–13）并回中 yaw0（stage14），但在下降回收阶段因既有 `normalized_cost=1.025847>1.0` 健康门停止，完成15/18 stages。没有 post-release N05、mission 或 flight。fixture verified detached/scene absent/landed；独立 PX4 readback 为 disarmed/landed，bridge DISABLED，控制输出0；容器 exit0。

证据：[运行报告](../evidence/n08-negative-side-localization-recovery-refusal-20261026-302.md)、JSON 和 artifacts run 目录。

下一子项 #303 仅在侧视回中后添加 15s neutral hold at z=1m，再开始原下降流程，以检查回中恢复是否消除下降开始时的原门限越线；不调整阈值。
