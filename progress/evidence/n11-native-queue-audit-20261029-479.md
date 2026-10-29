# #479 固定原始输入native队列审计

诊断完成；N11仍in_progress，正式0/3，Goal保持active。#478队列标准选择尚无用户回复，冻结规则与所有FAIL未修改。

## 执行与身份

使用#477完整MCAP，在network=none、ROS domain159的独立容器中只运行VINS/播放器/只读记录器，无PX4、planner或控制。复用已构建#449 trace/reliable诊断binary；对比当前VINS源码，仅rosNodeTest.cpp的只读trace和可靠QoS有差异，其余包括estimator.cpp/feature tracker字节相同。YAML沿用实际#477所有算法参数，仅改epoch/frame/output路径。QoS不同于live BEST_EFFORT，结果仅限诊断，不能替代现场完整验证。

录包IMU29684条、左右图像各3598帧；从MCAP实际反序列化header得到预期指纹，再与原生callback/同步消费trace比较。容器正常exit0，bag完成后10秒drain，VINS由SIGINT正常退出。

## 结果

全部原生callback source指纹与录包一致；3598对原始双目全部processed，catch-up drop=0、未解释配对=0。图像队列由事件顺序给出的保守prefix高水位左右均1；feature current始终1。IMU current-before-dequeue最大29、中位27，但OLS slope仍+0.003444442items/sim_s。因此现有严格零正斜率规则仍会判FAIL；未重算为通过。

另外提取实际production getIMUInterval函数体，在固定镜像真实C++编译运行队列fixture：同一当前积分区间，增加未来tail后before计数31→51，实际积分均为相同17条，remaining_future14→34。说明该指标确实包含未来样本；不等价于当前待处理图像积压。该fixture只关闭语义子问题，不证明任意长期负载有界。

## 产物与限制

[回放/原生审计](../../artifacts/replays/n11-20261029-479-native-queue/)、[协议/源码差异/提取函数](../../artifacts/n11-prepared/n11-20261029-479-native-queue/)。manifest、config、binary、输入指纹、native trace均记录SHA。source-diff-summary仅node差异，提取函数另外绑定原source SHA。

下一步仍需用户对[#478建议](../../docs/protocols/n11-queue-review-proposal.json)作决定。保留原规则则当前FAIL有效；批准重校准后才能实现/验证新定义并冻结，再开始新的正式三次。批准前不抬阈值、不删数据、不改counter、不靠同类飞行碰巧通过。结构检查与diff-check最终执行；本轮无新飞行。
