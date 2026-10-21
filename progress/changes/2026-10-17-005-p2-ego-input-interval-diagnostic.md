# P2 EGO 建图输入间隔诊断

日期：2026-10-17。对应对话摘要：[2026-10-17-005-p2-ego-input-interval-diagnostic.md](../../collaboration/dialogues/2026-10-17-005-p2-ego-input-interval-diagnostic.md)。

- 修改：`tools/probe_mapping_runtime.py` 现在记录 EGO camera pose 样本和配对深度/位姿源时间间隔分位数；本次 no-fault run 使用独立 domain/partition，没有控制、PX4 或目标发布器。
- 有效数据：run #12/#15 故障前配对间隔 p50 均为 0.033 s、p95 均为 0.132 s，最大值分别为 0.231/0.264 s。无故障 run #17 连续40秒保持 READY／TRACKING，收到470组配对输入、地图最多1799点，probe直接记录相机位姿；但出现25条 EGO timeout 告警，配对输入最大间隔0.495 s。它是有效 no-fault mapping 输出观察，不是无告警的干净更新基线；0.4 s 仍为 PROVISIONAL。
- 异常分析：run #14 在 EGO 最后成功更新 22.408 s 后仍收到 22.441 s 配对输入，推算 camera pose 在地图内，但 EGO 于 22.837 s 报告 timeout。run #17 的相机 Z 最低 -0.0094 m，离地图下界 -0.01 m 约0.6 mm；需核验边界余量，但 run #14 疑似 gap 时相机位于范围内部。EGO 输入 callback／同步／clock 延迟尚无结论。
- 排除：无故障 run #16/#18 的定位适配器锁定 `propagated_stale`，没有有效优化里程计／配对地图输入／占据点。#16 首次运行器清理未结束隔离 LaunchService 子进程组，准确清理后已修复 run 脚本；#17/#18 的进程组退出后没有活跃本轮节点。
- 验证：`python3 -m py_compile tools/probe_mapping_runtime.py ...`、run 脚本 `bash -n`、证据 JSON 解析通过；容器进程审计确认无活跃本轮仿真／规划器／定位／建图节点。
- 限制与下一步：虽然 run #17 记录了直接 camera pose 和 no-fault 成图，EGO timeout 告警没有按每次消息回调关联，只有一次有效 no-fault run。重复该运行并记录 EGO clock、source age 与同步 callback／队列延迟；评估地图下界后再校准超时和重复故障验收。
