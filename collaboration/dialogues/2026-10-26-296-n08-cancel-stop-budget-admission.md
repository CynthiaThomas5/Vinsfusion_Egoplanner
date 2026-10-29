# 对话摘要：N08 制动预算与准入（#296）

- 用户授权：按 N08 完成测试计划持续执行，采用 Goal 完成模式。普通单目标到达停止后结束，不要求返航；运动取消与普通 terminal stop 是不同出口。
- #257 compute-only 与 #260 execute runtime-contract SHA 相同；#212 是无目标漂移基线，EGO idle binary/health config 不同，不能作为同版本动态对照。
- 将实测 0.30992m 取消停车路径纳入 0.50m 候选前向停车包络。该候选沿用评估器原值，按 EGO 停车目标最大 0.45m 加 0.05m 前向连续参考管道设置；参考锚点偏差未证明有 0.05m 上界，因此还须由替代曲线地图证书和独立实测把关，范围仅限低速、前向、该取消协议。
- 同一配置值已接入 pre-enable/airborne raw-map corridor和 independent evaluator。#298证明不应把剩余到原goal的距离等同于停车距离，该值现只作诊断，精确替代stop spline仍过EGO fresh-map完整曲线/terminal-hold门。现有机体、0.24868m uncertainty、0.25m tracking margin 和 0.15m tracking limit均未放宽或增大。
- `bash tools/project.sh test` 通过361项与 navigation-adapter integration。下一项 #297：0.07–0.09m/s motion-cancel 冷启动试验。
- 未决：高窗口是否能在保留至少0.50m已认证通道时触发；完成后再冻结并执行3次普通单目标终点制动。
