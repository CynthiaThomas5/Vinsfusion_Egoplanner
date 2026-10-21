# GOAL C EGO receive syscall diagnostic #355

- **范围**：在 #353/#354 相同的run-local Fast DDS receive-buffer profile下，使用临时容器内 strace 记录 EGO socket 创建／绑定与 `recvfrom`／`recvmsg`／`recvmmsg` syscall 时间、FD和返回值。receive调用参数按raw形式输出，不解码buffer内容；没有修改canonical源码、config、QoS或sysctl。
- **socket关联**：strace记录进程771将FD 70成功绑定到UDP 62427；同一进程的回调线程TID 808名为 `dds.udp.62427`。该socket的实际 `rb=425984`，对应 #353/#354 的run-local profile。strace日志全程记录104,439次该线程对FD 70的成功 `recvfrom` 返回，没有该FD的失败返回。
- **复现结果**：本轮最长 pose successful-take gap仅0.392429 s，低于0.4 s freshness门，未复现 #353/#354 的2秒以上gap。这个短窗内有96次EGO wait返回 `unread_count=0`、一次ready/unread=1；回调线程成功从目标UDP socket返回308个数据报（间隔内观测最大调用间隔19.786 ms、median 0.990 ms）。这些数据报可能属于participant上的其它DDS流量，不能当作camera_pose样本证据。
- **同窗有效性与偏差**：gap内adapter只有1次RMW publish、独立reader只有1条pose回执；MapStatus从ready转到 `map_reset_acknowledged`，epoch相同但map_id改变。reader status gap样本的sample_lost累计已为1、rejected为0；该sample_lost回调出现在gap前约83 ms。之后localization报告 `propagated_from_future`，planner probe `timeout_before_ready`，没有B-spline。strace可能改变进程调度；这一run不是匹配输入、稳定map下的长gap复现。
- **解释边界与下一步**：该短窗证明EGO UDP接收线程可在DataReader history为空的wait期间从FD 70成功取出participant datagram，但不能识别topic或证明camera_pose进入DataReader history。长gap未复现、输入不连续且map reset、ptrace有开销，故不据此排除接收路径问题。下一轮使用更低开销的receive-path计数，在MapStatus/epoch/map_id稳定且adapter与独立reader均连续时复测；继续记录完整socket到reader边界，再回到vehicle-safe视角、多布局和轨迹执行验收。
- **Trace与运行范围**：主CTF 32个data/index文件、36,312,672 bytes，逐文件哈希复核通过；wait trace 37,044条、序号0–37,043无缺失，所有selected analyzers退出0。运行容器退出0，但planner未ready、未发送目标、无轨迹；没有controller、trajectory server、PX4、truth topic或control topic。
- **验证**：CTF SHA-256清单、run manifest与evidence引用哈希、evidence／manifest/milestones JSON解析、`python3 tools/project_status.py`、`git diff --check`和cached检查通过；index仍50项。结构检查只表示骨架一致，不能替代GOAL C运行验收。
- **证据**：[报告 #355](../evidence/p2-ego-pose-rmw-recv-syscall-trace-20261021-355.json)、[运行清单](../../artifacts/runs/p2-ego-pose-rmw-recv-syscall-trace-20261021-355/run-manifest.json)、[对话摘要](../../collaboration/dialogues/2026-10-21-021-p2-ego-pose-rmw-recv-syscall-trace.md)。
- **阶段状态**：P2保持passed；GOAL C保持pending。
