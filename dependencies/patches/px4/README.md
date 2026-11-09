# PX4 硬件诊断候选：同步边界计时

**HW10-SYNC-018/019，仅隔离构建验证，未部署，不用于飞行。**

019核验发现设备使用GCC13.2.1，018使用GCC10.3.1；旧018镜像保留作历史证据，**不作为下一轮上板镜像**。同一对补丁已在GCC13.2.1/稳定分支重新完整构建，候选入口为`artifacts/runs/hw10-sync-20261105-019/candidate-gcc13/HW10-SYNC-019-GCC13-DIAGNOSTIC-NOT-FLIGHT.px4`，BUILD_URI=`hw10-sync-019-gcc13-diagnostic-not-flight`。当前资源/文件哈希见[同工具链manifest](HW10_SYNC_BOUNDARY_GCC13_MANIFEST.json)：Flash2025908B/2064384B，余38476B；相对同工具链基线+1572B，静态SRAM1+448B。下文018构建数字是历史结果。

设备构建信息与PX4 stable通道镜像一致（GitHub release同版本资产的构建时刻不同）；已保存stable文件SHA及期望CRC`0x4f6ba085`。当前FlashCRC尚未实读，不能称回退验证通过；不得仅凭版本相同刷写。部署/恢复步骤见[019协议](../../../docs/hw10-sync-diagnostic-deployment.md)。 不加入 `dependencies/sources.json` 的默认补丁列表，不修改冻结仿真或当前飞控/Nano。它是计时候选，不是提高优先级/同步频率的修复。

## 基准与应用顺序

只在新建隔离checkout应用，原来源 `/home/ac/PX4-Autopilot` 保持只读：

1. PX4主仓库基准 `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`（实际飞控已记录版本），递归子模块按该提交锁定。
2. 在 `src/modules/uxrce_dds_client/Micro-XRCE-DDS-Client` 基准 `711aef423edd1820347b866d1e4164832df35d04` 上，`git apply --check` 再 `git apply` **hardware-sync-boundary-client.patch**，strip=1。
3. 在PX4根目录 `git apply --check` 再 `git apply` **hardware-sync-boundary.patch**，strip=1。父仓库gitlink不更换，补丁配对使用。
4. 全新构建：`BUILD_URI=hw10-sync-018-diagnostic-not-flight make px4_fmu-v5_default -j8`。若复用旧ExternalProject构建目录，子模块修改不会自动使外部项目build stamp失效；推荐新build目录。本轮手动只清除了对应build/install文件stamp，记录在run-local脚本。

许可：PX4改动及新C++/msg沿用BSD-3-Clause；Micro-XRCE-DDS-Client修改与新hook头沿用Apache-2.0。原许可不变。补丁SHA、工具链、板卡ID、镜像/ELF哈希与资源结果见 [HW10_SYNC_BOUNDARY_MANIFEST.json](HW10_SYNC_BOUNDARY_MANIFEST.json)。这是源码版本核对，不是对当前飞控flash逐字节读取/复现。

## 记录内容与约束

新增只在FC内部的 `uxrce_dds_sync_trace` uORB/ULog话题，**不加入DDS话题表、不发布控制、不开新ROS包**。每个同步回复一条，队列8；保留原1Hz周期、10ms RPC、任务优先级、传感器/EKF/控制/所有准入门。请求元数据固定8槽，丢失匹配就清REQUEST_MATCHED，不用最近邻补造。单XRCE任务拥有hook状态；不适用于多线程/多会话共享该全局记录器，若更换配置必须重新审查。

- 精确键：`request_timestamp`为FC originate HRT us，`agent_tx_timestamp`为DDS `timesync_status.remote_timestamp` 对应Agent epoch us。注意PX4原回调形参命名：`client_transmit_timestamp`实际接收Agent receive，`agent_receive_timestamp`实际接收Agent transmit，补丁按实际调用源映射。
- `submit_begin/end`：围住原framed send_message；`uart_write_begin/end`：该次同步提交内首/末串口write系统调用的边界，`serial_bytes_written`为成功提交字节和。
- `reply_poll_begin/end`：最后一次成功读前的缓冲检查加poll；`reply_read_begin/end`：最后一次成功read的边界；`reply_bytes_available`为紧邻poll前的FIONREAD结果，仅同步等待期间查询，-1表示未测/失败。失败/空读不覆盖最近有效读。
- `timestamp`为原同步回调已捕获的FC接收时刻。先执行原Timesync更新，再发布诊断，避免把新uORB发布插在原更新之前；差值仍按原回调捕获时刻算。
- 窗口内全部字段递增/非零/flags满足才作分段。发布sequence跳号、REQUEST_MATCHED缺失、logger dropout均保留，不能补造或把样本丢失算正常。

write返回不是UART物理发送完成；poll返回不是RX中断；缓冲非空但调用迟返，只支持FC驱动/调用/调度路径贡献，不能独断为任务优先级。缓冲空时的等待仍混有UART/转换器与调度；必要时需硬件边界，不能把它全扣给UART。

## ULog与资源验证

候选只给默认日志主题**追加**新话题，原默认主题保留。不能用只有一行trace的logger_topics.txt替代默认配置；如果现场已有自定义 `/fs/microsd/etc/logging/logger_topics.txt`，它会覆盖默认主题选择，须保留原文件/完整主题并核验trace确实存在，不能盲覆盖。本轮没有写SD卡或启动logger。

原版与最终候选均完整FMUv5构建通过；补丁在干净最小基线应用后逐字节等于构建源码；实际C++记录器+生成消息头的主机测试覆盖迟到/淘汰/失败/禁用/旧读；实际串口C源通过socketpair验证负载/返回码/超时及仅同步等待时查询缓冲。它们不替代NuttX运行时或实机时序。

Flash增加1580字节，候选使用2049581/2064384字节（约99.28%），余14803字节；链接SRAM1增加448字节。120字节消息的8深度payload队列另需960字节运行时空间，还有uORB元数据、logger订阅、分配器开销；静态链接RAM不是全部运行时RAM。新计时调用及FIONREAD、uORB发布的CPU/栈峰值和调度影响**尚未上板验证**，不宣称开销已合格。

候选位于 `artifacts/runs/hw10-sync-20261105-018/candidate-firmware/HW10-SYNC-018-DIAGNOSTIC-NOT-FLIGHT.px4`，原版重建对照在同run的baseline目录。两者manifest的git_hash都可能仍显示基准提交，不能凭d6f12ad1认候选；需核对完整文件SHA、`ver all`中的BUILD_URI和trace话题。原版重建镜像并未证明等同当前设备flash，不当作已验证的回退镜像。

## 后续运行判据（本轮未执行）

先核验板卡/可回退镜像与完整参数恢复路径，再安排有明确部署范围的未武装诊断；不自动刷写。首次不加EV，确认trace/原DDS均正常、日志保留原主题、没有CPU/堆/栈/丢包异常，再进入用户指定当前视角/两线程EV窗口（>=180s），原门限全部保持。对每条同步将ULog请求/Agent transmit键与同轮Agent原生/DDS记录精确关联。

若write提交拖慢，查FC发送/串口驱动；若缓冲已有数据但处理迟返，查FC驱动/调度；若read→callback拖慢，查FC解析/队列；若这些都快而RTT高，剩余转向物理UART/转换器/USB输入路径。没有判别证据不改优先级或周期。另行保留017的定位遥测锁定问题，不把同步诊断通过算全链路通过。

收尾恢复原镜像及参数并核验DDS/未武装/零输入；移除诊断环境。若回退或部署条件不齐，保持未部署状态。完整证据见 [018报告](../../../progress/evidence/hw10-sync-20261105-018.md)。

## 020实机边界结果与下一单变量候选

020在用户授权后实读原版CRC匹配、部署GCC13 trace、完成EV窗口，并已刷回固定stable原版/完整参数复核。有效窗口252s，FC/DDS精确配对249条（Agent另有242条），5条高RTT的Agent仅0.137–0.175ms，read后回调亦很短；其中一条FIONREAD已有9B但检查/poll耗7.056ms。固定NuttX串口驱动在buffer非空应立即通知POLLIN，因此支持FC调用/调度贡献，不支持把所有高RTT解释为Agent或纯空缓冲等数据。空缓冲样本仍混有线传输、分帧和调度，物理分界未唯一确定。

`hardware-sync-priority-candidate.patch`是**第三个、非默认、未部署**候选，应用顺序在上述Client/主trace补丁之后。基准仍PX4 d6f12ad1（加trace补丁）；BSD-3-Clause。唯一行为变量：DDS任务 `SCHED_PRIORITY_DEFAULT`→`SCHED_PRIORITY_DEFAULT+1`，即当前FMUv5 **100→101**。只越过同级MAVLink100，仍低于Navigator105、Commander140和更高控制/INS任务；不改周期、传感器/EKF、DDS流率或任何准入门限。用途是验证同优先级竞争，不能据此断言已经找出全部来源；若101无改善，不继续无依据提高优先级。

候选源码/构建在`artifacts/runs/hw10-sync-20261105-020/priority-checkout`，镜像在该run的`priority-candidate/HW10-SYNC-020-PRIO101-NOT-FLIGHT.px4`，BUILD_URI=`hw10-sync-020-prio101-candidate-not-flight`。最终构建/哈希/资源见该run的priority-manifest.json；本轮只构建未刷入，现场仍原版。下一轮在原门限、同测量代码/视角/EV负载下仅比较100/101，并包含原版恢复；任何部分/否定结果均保留，不能拿可选候选冒充运行通过。

### 021评估更新：不采纳101作为当前尾延迟修复

101已经在021实际刷入并确认运行，完成约252s未武装EV窗口后恢复原版。DDS为3/249条>10ms，独立FC记录为4/250（另有一条10.836ms未出现在DDS观察中），对照100为FC5/249；最大11.128→11.834ms，未建立可靠尾延迟改善。因此101镜像/第三补丁保留作可复现研究工件，**不是已接受的运行修复，不进入默认sources，不继续盲升优先级**。原020“尚未部署”描述保留为当时历史，当前现场是已恢复的原版100。

10ms始终是单条准入门，2s是有效同步到期；不另造“整轮每次都≤10ms”验收要求。本次EV和已记录EKF融合持续正常，与优先级方案未证明有效分别记录。下一项022只读TX排队/发送顺序验证，见[021报告](../../../progress/evidence/hw10-sync-20261105-021.md)。

## 022 TX排队与发送顺序候选

基准仍PX4 d6f12ad1c4f70ad3230afd7d86e971421e02fef4 / Client711aef423edd1820347b866d1e4164832df35d04。应用顺序：原hardware-sync-boundary-client.patch、原hardware-sync-boundary.patch、hardware-sync-tx-queue-client.patch（Apache-2.0）、hardware-sync-tx-queue.patch（BSD-3-Clause）、hardware-sync-first-candidate.patch（BSD-3-Clause）。**不应用priority候选**。前二增量诊断首次write前FIONWRITE；最后一补丁只移动原同步块到遥测flush前，100/1Hz/10ms RPC/原门限不变。均非默认。

两完整GCC13构建、干净应用/字节一致与记录器断言通过。A队列证据满足冻结判据后实际测试B；RTT P95 9.118→5.263ms，主测7/250→0/251超过10ms，EV/EKF持续正常；单窗口且不同epoch，不构成全场景保证。两阶段已恢复原版。下一项023剥离诊断，仅保留最小顺序修复并回归。镜像/源码/哈希/构建日志见artifacts/runs/hw10-sync-20261105-022；详见[022](../../../progress/evidence/hw10-sync-20261105-022.md)。

## 023 最小同步先发修复（无诊断依赖）

`hardware-sync-first.patch`直接应用于原PX4 d6f12ad1c4f70ad3230afd7d86e971421e02fef4（BSD-3-Clause），**单独应用，不叠加018–022的trace/TX/priority补丁**。Client保持711aef423edd1820347b866d1e4164832df35d04无改动。只将原同步块移至本轮遥测flush前，不变更块内逻辑、优先级100、1Hz条件、10ms RPC、DDS流率或健康门限。默认仿真sources不改。

实际原始块与其余规范化源码一致性断言、独立目录干净应用/字节一致检查通过；GCC13.2.1完整FMUv5构建通过。Flash2024360B，比同工具链原版重建+24B，静态SRAM46708B无增量；ELF无同步trace符号。原工具链共有RWX/ARCH_CHIP_UNSET等构建警告保留。镜像/哈希/实际回归与终态以[023报告](../../../progress/evidence/hw10-sync-20261105-023.md)为准，不由构建替代实机结果。
