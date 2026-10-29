# #550 N16资源/队列趋势证据

Goal完成模式。新增tools/n16_resource_evidence.py，从真实resource/cgroup/mapping及native queue JSONL读取源时间区间，校验native记录hash/count、epoch和序列、全窗口覆盖，报告CPU实际核使用量、内存、RTF与mapping/native待处理数、原生源滞后和待处理跨度的min/P50/P95/max/线性斜率/四分位时窗中位数。瞬时峰值不是失败门；不调用旧0.2s/队列2/CPU容量数值门，不改控制逻辑。

四时窗中位数连续上升且末窗最小值超过首窗最大值的持续分离增长，只标需要审查/INSUFFICIENT，不武断声称数学无界或触发拒飞。缺数据/不完整窗口如实不足，不补零。该模块仅资源子证据，不能替代核心进程存活、实际运动/控制及正常终态审计。

验证：17项resource/continuity/profile测试PASS，含突发回落、恒定队列、持续增长需审查、缺数据和源时间异常；N14真实短任务按实际goal区间格式复放OBSERVED、缺项空、无待审增长，不计600秒资格。产物artifacts/runs/n16-20261029-550-resources，py_compile、project_status和git diff --check。未飞行。下一步完整逐目标实际运动/到达/接触/进程证据与曲线生成、隔离运行集成及真实长时任务。对话collaboration/dialogues/2026-10-29-550-n16-resource-evidence.md。
