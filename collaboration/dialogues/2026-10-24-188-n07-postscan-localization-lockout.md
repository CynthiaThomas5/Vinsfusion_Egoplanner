# N07 #188 对话摘要：attached准入后定位锁存

## 约束

- 继续用户授权的N07 Goal完成模式，直到3次连续独立cold start全部通过。
- 保持镜像、runtime、spawn、wall layout、separated-return profile及健康/N05门限；不得在定位无效时起飞。

## 决定与结果

#188完成12/12支架扫描，attached N05 online/offline接受，freshness 0.112/0.156/0.040秒。释放时helper返回fresh DISARMED status错误；attachment detached、fixture已移除。独立读回PX4 arming_state=1且landed，bridge DISABLED。定位锁存`telemetry_stale`，所以没有post-release/current-area gate或飞行，N07计数仍0/3。

12秒只读探针在失效后观察到输入流新鲜，无法锁定更早的触发流/时间。结论不改变任何健康阈值。下一次#189沿用全部运行条件，在ready marker后立即启用只读freshness probe并贯穿释放后门禁窗口；释放后优先快速运行N05 gates，只有健康和准入全部通过才继续无目标悬停。
