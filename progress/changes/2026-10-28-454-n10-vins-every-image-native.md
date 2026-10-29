# N10.3/#454

归档 #454 严格native-input VINS stride1候选的否定结果，并修正离线报告中输出采样率标记，使其由实际 raw odometry 数量/源戳范围计算。原 acceptance 数值不变；候选未部署。证据见[报告](../evidence/n10-vins-every-image-native-20261028-454.md)，原始产物见 `artifacts/replays/n10-20261028-454-vins-every-image-native` 和 `artifacts/n10-prepared/n10-20261028-454-vins-every-image-native`。无生产源码、在线参数、PX4 或规划器变更。下一项基于原生 telemetry 特征数达到 `max_cnt=180` 的可观察饱和，单独验证提高候选上限的离线影响。对话摘要：[记录](../../collaboration/dialogues/2026-10-28-454-n10-vins-every-image-native.md)。
