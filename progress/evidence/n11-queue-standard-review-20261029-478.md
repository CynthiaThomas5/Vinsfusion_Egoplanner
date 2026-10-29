# #478 离线队列判据语义复核（待用户决定）

原规则不变：acc/gyr/feature的current_before_feature_dequeue OLS斜率必须≤0。#476/#477仍FAIL。

源码Estimator::processMeasurements在getIMUInterval(prevTime,curTime)之前采样整个accBuf/gyrBuf。该buffer包含当前feature积分所需的前一图像区间IMU及已异步到达的未来IMU；featureBuffer采样同样发生在pop前。计数不等于已定位的无界待处理工作积压。

两次真实运行feature current都恒1，IMU首尾四分段中位数都26，OLS分别0.005007和0.002432。各1/4窗口斜率有正有负。以预声明1sim秒HAC lag仅作诊断，斜率95%区间分别[-0.001313,0.011327]与[-0.001796,0.006659]，不作为新通过规则。该信息不证明长期有界，也不足以把微小正点估计认定为持续积压。

数学反例：永远处于[22,28]的25-3sin(0.8t)在120秒窗口OLS仍为+0.001288；严格符号规则会将解析有界序列判失败。另一个0.3items/s真实增长反例被诊断清楚区分。原始数组/时间戳全部保留，没有挑选或删行。

[诊断JSON与脚本](../../artifacts/reanalysis/n11-20261029-478-queue-audit/)、[图](../../artifacts/reanalysis/n11-20261029-478-queue-audit/queue-diagnostic.png)。

[具体建议](../../docs/protocols/n11-queue-review-proposal.json)：针对真实待处理工作和oldest-source-time语义重新取得校准依据，原buffer计数/high-water/slope继续报告，capacity/overflow/OOM/throttle不删除；必要只读telemetry经验证后在新版本冻结，再做新的正式3次，不倒算旧run。不是简单抬高斜率限值，不钳制计数，不新增在线门。

依据AGENTS.md“保持任务标准”约定，判据定义调整需要用户决定；已发出异步选择。用户批准前不修改冻结配置，不将#477计为正式通过。Goal保持active，此为首次出现的标准决策点，不标blocked。
