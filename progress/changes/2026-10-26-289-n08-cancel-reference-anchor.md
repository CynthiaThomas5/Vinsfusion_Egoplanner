# #289：N08取消停车参考锚点修复


## #289 N05前置结果

#289 fresh start 在N05 outbound完成后，return stage 3/6 首次触发`accel_bias_norm_exceeded`：VINS bias 0.150019m/s²超过既有0.15门，normalized cost=0.503、solver usable、solve 19.7ms。夹具detach/remove已验证，最终landed；未到post-release准入或mission。独立PX4/bridge probe读回DISABLED、disarmed/landed，3个控制topic各0条，随后project stop退出0。报告见[#289 N05拒绝](../evidence/n08-n05-accel-bias-refusal-20261026-289.md)。

同profile #288的最大bias为0.090592；#289在outbound约x=−2.02m升至0.074，并在return约x=−1.39m越限。现有证据支持跨fresh VINS epoch的估计偏置变化，但未归因内部根因。下一子项#290只改变fresh epoch，重复同一profile以检验位置相关复现；健康阈值保持0.15。
