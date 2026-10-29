# #481 N11离线队列判据重校准（执行中）

用户批准见[对话摘要](../../collaboration/dialogues/2026-10-29-481-n11-approved-queue-recalibration.md)。Goal范围仍为N11全部剩余任务，正式0/3。

实际修改：新增VINS补丁0021只读native pending work/source边界，登记source lock；新增acceptance_n11 revision9草案和独立评估helper；原revision8及旧FAIL不改。公共评估器按配置选择旧OLS规则或新native规则，CPU/内存/容量/缺数据检查保留。N11协议评估器支持按发布协议绑定config SHA及新runtime逐字节一致；评估入口支持显式config。正式放行尚未发布。

验证：固定镜像独立真实vins包构建45.9s成功（仅上游deprecated ConstPtr告警）；75项相关单元测试通过；git diff --check通过。独立候选`/home/huangxiaocheng/n11-20261029-481-native-work/project`，未覆盖#464原始树。新vins_node SHA `4d19e003654b2a1a2ec1996b07701a5ec4c304622e410965a7b9ccaac06f6800`。固定输入生产BEST_EFFORT回放运行中，不启动PX4/planner。

产物：`artifacts/n11-prepared/n11-20261029-481-native-work/`；方法见`docs/n11-native-work-calibration.md`。下一子项#482完整GUI校准；通过后冻结新标准和runtime，再三次新冷启动。当前未停止Goal，无正式计数。

后续结果：最终77项相关测试通过。#482全部适用正常指标通过并安全落地停止；#483冻结revision9/新runtime/source/binary/evaluator；#484正式01完整PASS。原草案/失败报告留存，校准不倒算。正式矩阵持续执行中，最终状态见CURRENT与N11最终审计。
