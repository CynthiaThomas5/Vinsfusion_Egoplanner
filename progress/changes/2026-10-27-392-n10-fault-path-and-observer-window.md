# #392 N10 故障路径与观察器安全终止修复

对话摘要：[故障结束路径、ACK 时间域与观察器边界](../../collaboration/dialogues/2026-10-27-392-n10-fault-path-and-observer-fix.md)。

审计 EGO timeout → navigation abort → bridge/PX4 的状态链。桥接器对未确认 `NAV_LAND` 增加有限重试和 ACK/原生状态判断；到达重试上限仍保持 LANDING，只有 PX4 同时报告 landed 与 disarmed 才转 LANDED。修复 ACK 关联在 DDS 时间同步启用时误比 Agent/PX4 时钟的问题；修复 REQUEST_ARM 的 `_begin_landing` 旧签名调用并覆盖该分支。

统一真值、对齐、规划、bridge、接触及资源 observer 的关闭条件，失败任务 `flight.json` 不再被当作安全终止。资源观察在验证安全终态后继续 3 秒；不完整窗口仍为不足，不影响 runtime 控制。#391 的 PX4 状态历史被重新评估为 `AUTO_LAND(18) → failsafe DESCEND(12)`，紧急关闭读回为 disarmed/landed/control-disabled/zero-control 且 `nav_state=OFFBOARD(14)`；原始文件不变。

验证：`bash tools/project.sh build ros` 17 包通过；`bash tools/project.sh test` 471 tests、navigation adapter integration 与 official EGO policy probe 通过；离线 #391 divergence evaluator 复算输出新状态历史；`git diff --check` 通过。没有启动 SITL。源审计与限制见[证据报告](../evidence/n10-fault-path-audit-and-observer-window-20261027-392.md)。

限制：无真实断流/进程退出的本版本 PX4 末态证据；#391 的失败起因仍不唯一，跟踪/漂移与场景几何预算尚未通过；resource/query 数据仍不足。当前 N10.3/#392 只完成源码/工具层修复与测试，不代表 N10.3 或 N10 通过。
