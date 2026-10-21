# GOAL C EGO Fast DDS ACKNACK 与重传诊断 #378–#379

- **用户指令**：继续 #372–#377 后的 EGO pose-reader 序号空洞诊断。
- **约束**：只推进单D435i planner-only 仿真；保护工作区原有 staged/unstaged 修改；实验产物只写 run-local artifacts；不发goal、不启动PX4或trajectory server、不订阅truth/control、不改canonical QoS、socket缓冲或0.4 s freshness gate。
- **决定**：复用#377 run-local EGO overlay，运行两次隔离仿真。#378扩展metadata capture以包括ACKNACK/HEARTBEAT；因目标run未保存ACKNACK submessage flags，#379补采flags以可靠解码位图。
- **已确认**：#379捕获reader ACKNACK精确请求615，flag0x01表示little-endian；writer向精确reader重发615发生在5.120 ms后，EGO receive API紧接着返回，Fast DDS listener随后一次报告615–662，48条history更新均成功。#378同样的位图与同序重传对齐，解码包含缺口399/402，但此轮endianness依据来自#379，故作为跨run推断。#378的399/402回执发生在下一次successful take之后。
- **未确认**：首份DATA为什么未由EGO receive API返回。socket drops与接收队列来自participant UDP socket汇总计数，不能关联至单个sequence；内核/transport drop具体原因仍未知。
- **收尾复核**：发现#378来源清单把日志和运行结果误列为`run_local_inputs`。已改为24项实际输入并重算条目哈希/大小；采集后修过元数据变量的`run-live.sh`另列为post-run更正，原执行版哈希未留存，现有捕获记录说明过滤器未变。更新后的run-manifest哈希已传播到#379来源清单和综合证据报告；两份manifest中的174/175个文件哈希均通过，数据与诊断结论未改。
- **决定**：不调整QoS、host socket/kernel buffer或freshness gate；继续针对socket/drop reason和RTPS序号做定向关联。P2保持passed，阈值PROVISIONAL，GOAL C pending。
- **记录**：[轻量证据报告](../../progress/evidence/p2-ego-fastdds-acknack-recovery-20261021-378-379.json)、[变更记录](../../progress/changes/2026-10-21-028-p2-ego-fastdds-acknack-recovery.md)、[run #378](../../artifacts/runs/p2-ego-fastdds-acknack-recovery-diagnostic-20261021-378/run-manifest.json)、[run #379](../../artifacts/runs/p2-ego-fastdds-acknack-bitmap-flags-diagnostic-20261021-379/run-manifest.json)。
