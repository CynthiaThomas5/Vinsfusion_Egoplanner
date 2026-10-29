# #479 固定输入原生队列诊断

新增工作区artifacts内隔离回放协议、MCAP指纹、源码差异、原生callback/processed audit，以及实际getIMUInterval函数提取C++fixture。仅更新证据/CURRENT/milestones，不改canonical VINS/飞行配置/冻结验收文件。

结果：29684 IMU、3598对图像全部native接收并处理；drop/未解释pair为0，image/feature队列高水位1，acc/gyr raw buffer OLS仍+0.003444。实际函数fixture验证未来tail改变buffer数、不改变当前积分工作。可靠回放QoS与live不同的限制明确保留。独立容器正常exit0，无PX4/planner/新飞行。

Goal仍active，正式0/3；标准决策仍待用户，当前原规则FAIL保留。下一步按决定继续，不再次无新假设重复同类飞行。project_status/diff-check最终执行。对话：[摘要](../../collaboration/dialogues/2026-10-29-479-n11-native-audit.md)。
