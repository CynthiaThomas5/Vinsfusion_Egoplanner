# GOAL C EGO RTPS receive API 与 UDP socket drop 诊断 #369–#371

- **用户指令**：延续“继续完成文件夹下 GOAL”的授权。
- **适用约束**：只推进P0–P6单D435i仿真；旧来源只读；不伪造package或launch；保护已有staged/unstaged修改；本轮不使用真值、不发布控制、不启动PX4或trajectory server；RTPS探针只写头字段，不保存应用payload或PCAP。
- **问题**：#366–#368的loopback DATA可见性不能证明EGO participant收到目标writer报文。后续先在EGO的接收API返回缓冲区解析目标DATA头，再用`/proc`只读采样判断participant UDP socket的累计drop计数是否与精确take gap同时变化。
- **决定**：保留#369原始结果，但将其实体ID预过滤和单标量SequenceNumber解码缺陷标为限制；按mapping writer完整GUID前缀和RTPS high/low 32位大小端解析重跑#370；#371以20 ms周期采样fd/inode、UDP端口、rx_queue与drops，并与相邻等长窗口比较。#371首次分析误用了前一轮的固定VPID，完整保留并排除该次分析；最终分析从`ego-trace-selection.txt`读取PID后重跑。
- **已确认**：#370的2.496392 s gap内有51个loopback唯一DATA序号，44个序号从EGO receive API缓冲区观察到并与loopback吻合。#371的2.294765 s gap内有47个loopback唯一序号，46个从EGO receive API观察到并匹配；端口65179的socket drop计数跨gap bracket增加58，前后等长区间增加40和28，全47.5 s增加1219。#371 gap内626次wait为not-ready/unread=0，末尾ready时history为12；状态lost/rejected为0，listener仅data-available。目标writer数据已到达EGO进程接收API，但DataReader history/take没有同期就绪证据。
- **未确认**：socket drops是该participant端口所有流量的累计计数，不能映射到pose topic或序号112；loopback和receiver探针均未建立完整捕获保证。#370末尾出现一次sample-lost callback，#371没有；跨run不稳定。接收API返回也不代表DataReader history准入或成功take。
- **状态与下一步**：P2仍passed，健康阈值PROVISIONAL，GOAL C仍pending；milestones不变。继续只读追踪Fast DDS接收处理、reader匹配、history写入与wait-set通知，尽量将目标DATA序号与这些状态对应。
- **证据**：[轻量报告](../../progress/evidence/p2-ego-rtps-receive-api-socket-drop-diagnostic-20261021-369-371.json)、[变更记录](../../progress/changes/2026-10-21-026-p2-ego-rtps-receive-api-socket-drops.md)、[#369–#371运行清单](../../artifacts/runs/)。
