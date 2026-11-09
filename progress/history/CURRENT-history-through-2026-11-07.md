# CURRENT 历史交接归档（截至 2026-11-07）

本文件是从 CURRENT 移出的历史记录。标题中出现的“当前”“活动”等均是当时原文，不代表今天的进程、会话、参数或操作指令。执行任何硬件操作前只认 `progress/CURRENT.md` 和新鲜的设备状态回读。原始 evidence/change 路径保持不变。

## HW10-VIEW-032（已停止，数据保留）

- 暂停初查：PC路径出现16.166s接收空窗，用户确认左右目图同时停；Nano全会话optimized最大0.330s、左右目0.206s、初始化后健康invalid0，证据指向显示链路，SSH/接收/渲染具体位置待定位。保留当前会话不重启，见[evidence](../evidence/hw10-view-pause-20261105-032.md)。

- 用户明确取消膨胀地图，要求重来并细化轨迹。031 map-only/两个旧视图及旧session已正常停止；032为新perception --visuals epoch d57feb4998404e6481272c9146145264。Nano重启后当前会话停止，无map/规划/桥接器进程。
- 轨迹线宽从.025改为.005m，默认MoveCamera/NVIDIA渲染保持。PCview335692、RViz335693，圈记录器335920；源/owner文件在artifacts/runs/hw10-vins-thin-view-20261105-032，Native硬件session统一管理相机/VINS/2个relay。当前显示为live，不是旧圈快照。
- 圈记录器到900秒上限后保存5609姿态；用户未确认返回起点，不判绕圈完成。Nano相关PID均已退出、旧owner快照留存且状态文件清理；`rmem_max`恢复212992。PC端旧view/RViz在本轮迁移开始前仍运行，需关闭并验证。
- 031地图代码/PROVISIONAL体积修正留存，但当前不运行地图；失败/修正/真实点云/用户取消见[031](../evidence/hw10-map-view-20261105-031.md)。030旧圈已保存且旧会话关闭；主线仍028，当前不追加算法/飞行验收。

## 用户当前查看：HW10-VIEW-030（原生VINS实时显示保留）

- 用户要求RViz可拖动且有官方式稀疏点/左右目跟踪图。源配置已加MoveCamera默认工具、固定world观察、15Hz；PC NVIDIA PRIME/OpenGL4.6实证，替换旧约900%CPU未用NVIDIA的无响应窗口。原生image/points/history/双相机Marker真实接收、每类RViz订阅1、无解码错误。
- 活动Nano perception --visuals run=hw10-vins-official-view-20261105-030，epoch6812e30a222546e0ba2ede44bff26508；PC域83/localhost view328287、RViz328402，实际start_ticks/命令见030/retained-processes.json，Nano进程状态nano-active.json。原Agent独立active；无EV/模式/控制/参数写入。
- 用户完成第二圈：完整session首尾估计差约0.328m（水平方向0.326m/高度0.0356m），yaw差约2.61°；初始3条等待后持续valid，无epoch切换/锁定；返回静止最后10条估计稳定。无独立精确回位测量，不当绝对误差/导航通过；当前未启loop_fusion校正。增量记录器晚接入途中，已排除其错误起点，使用完整保留路径。
- 用户查看需要，当前**原生实时画面仍在运行**；圈记录器已停。029圈数据/PNG与旧快照保留，旧RViz已关闭替换。新正式试验前保存并身份核验停PCview/RViz，再Nano正常hardware.sh stop，核验runtime/rmem恢复；不盲起第二套相机。
- 显示修复/观察交付完成，未自动推进算法或飞行。唯一主线下一项仍HW10-EV-028；027A板上高度用户接受通过/装机后复测保持，HW08/完整HW10未完成。证据[030](../evidence/hw10-vins-native-view-20261105-030.md)，[029](../evidence/hw10-circle-view-20261105-029.md)。

## 当前交接：HW10-EV-027（当前板上高度功能已由用户接受通过）

- **用户最新决定027A**：当前高度验证先按通过，装机后再复测。保留手持误差/未独立精度量测限制；不再要求本测试板重复高度验证。通过范围仅为027板上高度功能，不外推完整HW10/最终安装/飞行。见[接受记录](../evidence/hw10-height-bench-acceptance-20261105-027a.md)。本次只更新记录，无设备操作或参数变化。

- 普通单变量高度台架检验/精确恢复已完成：临时HGT_REF1(GPS)→3(Vision)并重启，其他源/噪声/门限/023固件/024桥接器/Agent不变；EV_CTRL11/MAG6与026协议相同。用户实测10cm上移：EV10.09cm、PX4local9.98cm，返回高度残差约2.5/3.5mm。有效EV高度观测同向，支持采用Vision作后续EV台架高度基准，不支持再翻转Z；单轮/手持/不同epoch，非全轴/飞行精度资格。
- 主窗203.81s：EV5218、最大94.086ms间隔/无源戳倒退；4077健康全有效，202同步P95 5.094/最大9.798ms、0条>10ms；三路selected aid各408全fused/拒绝0、ULog无dropout，动作无reset。伴随约5cm水平变化未独立量测，不评价水平精度。
- 初次重启USB旧节点尚存导致提前连接/恢复失败，未启动EV；待实际重枚举后继续同一次候选。辅助等待现检查旧inode/cycle及应用by-id排除bootloader，3类模拟状态PASS，失败记录保留。未以重试改候选或门限。
- **当前已恢复原HGT_REF1/EV_CTRL0/MAG_TYPE0并重启**，1095项原值零差异/logger40off，Agent76673未变、runtime空、全部owned退出0、终态DDS五类正常/未武装/输入publisher0。dirty journal已由027/recovery-complete.json闭环，无待恢复参数/进程；023同步修复仍保留。高度方案仅验证，未永久启用3。
- 唯一下一子项 **HW10-EV-028**：显式采用已验证Vision高度基准，在现有空间量好小水平位移并完整记录转角/返回，补齐026剩余动态出口；不默认0.5m、不重做DDS实验，不启动控制/武装/飞行。HW08最终安装/机型、HW10控制/接管等仍未通过。
- 停止原因：027有界对照与恢复交付完成，父HW10仍in_progress。证据[027](../evidence/hw10-ev-height-20261105-027.md)，产物artifacts/runs/hw10-ev-height-20261105-027及-perception；高度参数说明已补docs/hardware-running.md。

## 当前交接：HW10-EV-DYNAMIC-026

- 普通有界动态板上EV采集/分析/恢复交付完成，父HW10仍in_progress。用户确认仍在测试板，明确选择动态EV、接回PC USB；023固件/024桥接器保持，无control/模式/武装/飞行/刷写，原门限保持。
- 主窗549.79s：EV14077条、最大185.914ms间隔、源戳无倒退；健康10995条全部有效；545条同步P95 5.767/最大9.423ms、0条>10ms；selected三路aid各1099全fused/拒绝0，ULog无dropout。融合/连续正常不等于高度/尺度正确。
- 用户澄清空间不足、实际移动小于指令；早先0.5m/0.3m回复不是独立量测，**撤回尺度偏小判断**，实际距离unknown，不改VINS比例。前/左/上EV投影方向正确，观察位移约0.370/0.278/0.364m只作记录；yaw窗内约+68.5°，90°终点确认在600s观察器结束后，未算完整转角/返回通过。
- 高度未通过：抬高EV NED z变化-0.364m、PX4 local z约+0.329m。生产ENU→NED/固定yaw检查及19+8项/独立参考测试通过；发送端up→负Z正确，不直接再翻转Z。ULog气压高度+0.375m，而selected bias校正后EV-hgt observation约+0.311m；动作内无reset。HGT_REF1(GPS)/GPS-hgt未激活/baro-hgt激活，须核对高度参考/偏置，根因未唯一确定；原始接收EV话题未记入默认ULog，边界保留。
- 终态临时EV_CTRL/MAG_TYPE已恢复0/0、1095项零差异，logger40/off，原Agent76673 active/NRestarts0未动，runtime空/无owned进程，终态DDS五类新消息/未武装/输入publisher0。无临时会话或参数待恢复，023修复仍生效。
- 唯一下一子项 **HW10-EV-027**：现有ULog高度参考/偏置定向核对与最小单变量未武装复测方案；必要时仅量好空间允许的小幅升降，不默认0.5m、不盲改Z/门限。HW08最终安装/包络和实际机型仍未通过，不转控制/飞行。
- 停止原因：026有界验证得到部分/否定结论并安全收尾，非动态或父HW10通过。证据[026](../evidence/hw10-ev-dynamic-20261105-026.md)；[025只读核对](../evidence/hw10-ready-20261105-025.md)，机型问题不阻塞零控制板上EV但控制依赖保持。原始artifacts/runs/hw10-ev-dynamic-20261105-026及-perception。

## 当前交接：HW10-EV-024

- 普通有界退出修复完成：main只在control模式访问supervisor；EV-only/compute-only正常销毁，control活动态disable先于destroy、终态不重复disable保持。新增5项mock入口测试，修复前3错、最终全通过；同步门控边界回归通过。
- Nano原生colcon曾安装旧缓存，首次生命周期验证也跑到旧版失败；均保留未算通过。强制重建安装/刷新实际colcon缓存，再普通构建后，PC/Nano源/build/install全部12个Python文件逐项一致。node SHA72b9b7ed…2192。
- 真EV-only程序SIGINT返回0、约0.425s退出，无Traceback；19条状态均未武装，只有EV publisher1/控制0，退出后所有输入publisher0。未启相机/VINS，不把生命周期验证算EV融合或导航测试。
- 终态1095项零差异、未武装/logger off、023固件仍生效；原Agent76673 active/NRestarts0未动，runtime空/无残留。无参数/固件/进程待恢复。HW08/HW10保持in_progress，无控制/飞行授权。
- 唯一下一子项 **HW10-READY-025**：只读核对实机主线的HW08安装/包络、机型一致性及剩余出口，明确下一项实际可执行缺口；不追加RTT试验、不推断缺失测量、不自动转控制/飞行。
- 停止原因：024有界修复及验证完成。证据[024](../evidence/hw10-ev-20261105-024.md)，产物artifacts/runs/hw10-ev-20261105-024。

## 当前交接：HW10-SYNC-023

- 普通有界最小修复/回归交付完成：原PX4只移动同步块到普通遥测flush之前；无trace/队列采样/Agent插桩，100/1Hz/10ms RPC及全部门限保持，GCC13完整FMUv5构建/干净应用PASS；Flash+24B/静态RAM不增。
- 两个约252s窗口各DDS251条、均0条>10ms；P95 5.205/4.970ms，最大8.653/8.972ms（022-A P95 9.118/最大11.429ms）。EV连续/健康全有效/无锁定/无源戳倒退。首轮ULog有263ms等dropout不算完整融合证据；r2仅临时日志缓冲40→80，主窗无dropout，三路aid各504条全fused/拒绝0，结束恢复40且off。
- 生产门控方法内存回放6289次EV/mode/setpoint均连续/blocked空；不是实机控制测试。当前固件**已采纳并保留为未武装地面基线**，URI hw10-sync-023-sync-first-minimal-not-flight，SHA8e170b1c…59d1；不再是022恢复的原版。原无条件回退计划经通过后的采用决定替换，固定原版/CRC回退路径保留。见023/adoption-decision.json。
- 终态新鲜未武装、1095项零差异/logger Not logging，原Agent76673 active/NRestarts0从未重启，runtime/overlay空；10s DDS五类新消息、零输入publisher。所有本轮进程已停止，无临时配置待恢复。HW10/HW08保持in_progress，无飞行授权。
- 未解：EV-only节点受控退出时访问不存在的supervisor而报AttributeError/退出1；运行主窗正常，未混入固件补丁。唯一下一子项 **HW10-EV-024**：退出分支保护与验证，保留控制模式安全退出逻辑；不再自动开启延迟试验或飞行。
- 停止原因：023有界交付/采用完成。证据[023](../evidence/hw10-sync-20261105-023.md)，产物023/023-r2及两组-perception。

## 当前交接：HW10-SYNC-022

- 普通有界TX队列/顺序对照及原版恢复完成。A 250条FC：7条>10ms；B仅同步先发251条：0条>10ms，RTT中位4.626→2.790/P95 9.118→5.263/最大11.429→6.793ms；队列中位166→0B。支持顺序修复贡献，不宣称所有场景消除长尾。
- 两组约253s EV连续、健康invalid0/无锁定，EKF三路全部fused/拒绝0，主窗日志无dropout。不同epoch/各一个窗口，非动态精度或飞行资格。原优先级100与全部门限保持。
- 两阶段均已刷回固定原版。终态ver18:50:48/localhost、1095项零差异/logger off、原Agent76673 active/NRestarts0、runtime/overlay空，终态DDS新消息/未武装/输入publisher0。无待恢复状态。
- 唯一下一子项 **HW10-SYNC-023**：去除诊断仅保留最小同步先发修复，完整构建及已授权未武装回归后决定采用。当前仍原版；HW10/HW08未完成，不转飞行、不升门限。
- 停止原因：022有界交付完成。证据[022](../evidence/hw10-sync-20261105-022.md)，原始022/022-a/022-b及-perception。执行范围仍为用户授权DDS延迟修复及恢复。

## 当前交接：HW10-SYNC-021

- 普通单变量对照/原版恢复完成：实际部署101、top101 (101)与基本15条trace确认；中断后核验已完成刷写，未重复操作。维持全部门限/1Hz/流率，无武装/飞行。
- 完整主测251.93s：DDS3/249条>10ms；独立FC250条连续序号中4条>10ms（额外10.836ms不在DDS观察中）。100对照FC5/249，最大11.128→11.834ms、中位4.676→4.765ms；没有可靠尾延迟改善，不采纳101，不继续盲升优先级。
- 澄清：10ms是单条准入门、2s是最近合格同步期限，不是全窗口零超限新契约。主测EV6502条、最大接收115.982ms，无>200ms空窗/源戳倒退/锁定；三路aid各504条全fused/拒绝0、主测无ULog dropout，静态窗口连续正常，不外推动态精度/飞行。
- 已刷回固定原版并通过上传CRC，最终ver18:50:48/localhost、1095项零差异、logger Not logging。Agent71508原配置active/NRestarts0、headless/.runtime空/rmem212992、无overlay；终态DDS新消息/未武装/零输入，无待恢复固件或参数。
- 唯一下一子项 **HW10-SYNC-022**：回到100基准，只在sync提交前测FIONWRITE软件TX排队；有正证据才用同测量比较先sync后遥测的单一顺序改动。保持门限/频率/优先级/传感器，软件队列0不证明物理空闲。既有未武装维护/恢复授权沿用，不加契约外冷启动次数、不转飞行。
- 停止原因：021对照与恢复交付，101研究不采纳，剩余尾延迟来源未唯一确定；HW10/HW08仍in_progress。证据[021](../evidence/hw10-sync-20261105-021.md)，原始artifacts/runs/hw10-sync-20261105-021及-perception。

## 当前交接：HW10-SYNC-020

- 用户已明确授权CRC匹配后诊断部署/未武装采集/原版恢复，本轮均实际完成。原版FlashCRC4f6ba085实读匹配，019.2缺口关闭；019/GCC13 trace上板基本日志15条全flags15，主测252.19s。没有武装/真实控制/飞行，原门限保持。
- 250同步中249条FC精确配对、242条Agent配对；全部5条高RTT完整覆盖，最高11.128ms，Agent0.137–0.175ms、读后解析很短。一条已有9B但查询/poll7.056ms，支持FC调用/调度贡献；其他等待仍混UART/转换器/调度，不能全部归一方。
- EV6620条/258.12s，无>200ms接收空窗、无定位锁定；主测最大100.568ms，估计相对起点最大2.15cm（非真值误差）。aid位置/高度各504、yaw503采样全fused/拒绝0；ULog有614ms等主窗dropout，持续融合资格未闭环。Nano CPU中位95.76%，本轮不启USBmon，不能唯一归因与017差异。
- 形成第三非默认补丁：仅DDS优先级100→101，仍低于Navigator105/Commander140/控制/INS。独立GCC13完整FMUv5构建、干净补丁应用及实际反汇编#101确认通过；镜像和manifest在020/priority-candidate及priority-manifest.json。**该101候选尚未部署，未称修好**。
- **已恢复原版**：上传CRC通过，最终ver为2026-05-13 18:50:48/localhost，1095项与原备份零差异，logger Not logging。Agent68828原配置active/NRestarts0/headless/.runtime空/rmem212992，终态DDS新消息/未武装/零输入。无参数或固件待恢复，历史待授权/候选现场状态均已解除。
- 普通有界交付完成；唯一下一项 **HW10-SYNC-021**：同视角/相同trace与Agent记录、同GCC13下对100→101做单变量未武装EV/资源对照，并恢复已核验原版；保留门限，不盲目继续升优先级、不重复确认已授权的同类维护、不飞行。HW10/HW08仍未通过，017源超时独立保留。
- 停止原因：实际诊断/原版恢复/最小候选构建完成，非延迟或持续融合修复通过。证据[020](../evidence/hw10-sync-20261105-020.md)；原始artifacts/runs/hw10-sync-20261105-020。

## 当前交接：HW10-SYNC-019.1（019仍未完成）

- 普通有界只读来源/参数/部署准备交付；未重启/刷写/EV。新鲜system1/component1未武装，1095项公开参数与012原备份零差异，logger明确Not logging。SD BSON43项（37CAL）与当前一致；MTD FTP0B不当raw备份。
- 匹配设备的PX4 stable原版已固定：SHA b50b2755…e403，d6f12ad1/FMuv5/13.2.1/2026-05-13 18:50:48/stable构建信息一致。GitHub release同版本镜像18:40时刻不同，不作精确回退。期望完整应用区CRC0x4f6ba085经上游算法交叉核验，实际FlashCRC未读，回退核验未通过。
- 发现018 GCC10与设备GCC13差异，已用经Arm官方SHA核验的13.2.1在019隔离clone同补丁完整重建基线/候选。新候选Flash2025908/2064384B，余38476B，增量1572B；SRAM1+448B，topic queue另960B运行时。018镜像仅历史，不上板；实际CPU/堆/栈未测。
- 新只读CRC工具4项测试/真实镜像上游交叉校验通过；部署恢复协议和GCC13manifest已就绪。Nano Agent65857 active/NRestarts0/headless/.runtime空/rmem212992，终态DDS新消息、未武装/零输入；无参数/镜像待恢复。
- 唯一下一子项 **019.2**：明确维护范围后，未武装短暂重启进入bootloader，只读身份/FlashCRC；不匹配则不擦写并返回原应用。已提出范围选择，尚未收到明确回复，不执行重启/刷写。只有用户同时授权且CRC匹配，才扩展020诊断固件采集及恢复。
- SYS_AUTOSTART12001/CA_ROTOR_COUNT8/MAV_TYPE14原值保留，实际机体/控制一致性仍待HW08核实；017定位生产超时独立保留。停止原因：019.1准备交付，019.2所需维护范围待确认，非功能通过。
- 证据[019](../evidence/hw10-sync-20261105-019.md)、[协议](../../docs/hw10-sync-diagnostic-deployment.md)；原始artifacts/runs/hw10-sync-20261105-019。

## 当前交接：HW10-SYNC-018

- 普通单项完成：实际PX4 d6f12ad1/Client711aef42隔离基线与FC同步边界计时候选均完整FMUv5构建通过。原来源、当前飞控和Nano运行环境未改，不部署/刷写/飞行；不是同步修复或HW10通过。
- 两补丁保存在dependencies/patches/px4（不进默认sources）；trace记录同请求submit/write、等待期间FIONREAD/poll/read、同步回调，精确originate/Agent transmit键。原1Hz/10ms RPC/优先级/10ms/2s/0.615998s等门均保持。用户态边界不能冒充物理UART中断/收发完成。
- 最终Flash2049581/2064384B（99.28%，余14803B），比基线+1580B；链接SRAM1+448B，uORB队列payload运行时另960B及元数据。实际CPU/堆/栈开销尚未上板验证。
- 实际记录器+生成头C++断言、实际串口C/socketpair返回值/数据/超时/FIONREAD断言通过；两补丁干净应用后字节一致，结构与diff检查通过。候选BUILD_URI hw10-sync-018-diagnostic-not-flight；原版重建不冒充设备flash备份/已验证回退镜像。
- 只读终态Nano Agent65857 active/NRestarts0、headless、.runtime空/rmem212992、无临时overlay；本轮无会话和参数/固件待恢复。
- 唯一下一子项 **HW10-SYNC-019**：可回退镜像与诊断部署/未武装边界采集协议核验，补齐设备镜像身份/恢复验证和运行条件后再安排采集，不自动刷写。017定位生产间歇超时独立保留。
- 停止原因：计时候选与离线构建/资源验证交付，实机根因修复/持续融合未完成。证据[018](../evidence/hw10-sync-20261105-018.md)、[补丁说明](../../dependencies/patches/px4/README.md)；原始artifacts/runs/hw10-sync-20261105-018。

## 当前交接：HW10-SYNC-017

- 普通有界当前视角/关闭桌面/两线程未武装EV同样本分段完成；主测214.78s，211/213同步精确配对。Agent中位0.141ms，6条高RTT中4条Agent占<2%、2条约3ms；外部剩余中位约9.976ms（高RTT子集）。USB完整OUT中位0.098ms。主项仍在Agent外部，不等同已唯一归为飞控，Nano内核USB/UART等待尚未分开。
- 本次带计时EV负载CPU忙碌中位98.5%、可用内存中位2814.9MiB；计时开销保留，不能外推无工具负载。约214s后telemetry_receipt_stale锁定，原生solver日志相邻0.654s间隔；连续融合仍未通过，不放宽门限。有效段估计相对起点最大2.0cm（非真值误差）、三路aid采样各430条全fused/拒绝0；不能截断失败尾部判通过。
- 收尾初末1095项参数零差异/原0/0、ULog11145508字节；Agent原库/1M/v4恢复，PID65857 active/NRestarts0（本轮诊断受控重启，旧21640已替换）。临时overlay/usbmon撤销、自有进程停/.runtime空/rmem212992；终态DDS五类新消息、未武装、输入publisher0；桌面保持关闭。
- 未改生产代码、固件、优先级或10ms/2s/0.615998s等门限。假设“Agent是高RTT主项”不获普遍支持，少数3ms贡献与定位性能故障保留。停止原因：同样本诊断/安全恢复交付，非修复或父HW10通过。
- 唯一下一子项 **HW10-SYNC-018**：实际固件基线下FC串口提交/同步回调边界计时候选和资源审查，进一步区分UART与FC调度后选最小修复；不直接部署/刷写/飞行。定位生产超时作为独立HW10未解项保留，后续单独复核。
- 证据[017](../evidence/hw10-sync-20261105-017.md)；原始artifacts/runs/hw10-sync-20261105-017及-perception。

## 当前交接：HW10-HEADLESS-016

- 用户要求释放Nano桌面资源：停止gdm并将默认启动改为multi-user.target，保留桌面包/JetPack/ROS。空闲快照可用内存增加约644MiB，非负载或RTT收益证明。
- SSH/网络正常，系统级Agent21640 active/NRestarts0；10s DDS五类正常、未武装、输入publisher0。无EV/控制/飞控参数改动。未重启测试；恢复命令见[016证据](../evidence/hw10-headless-20261105-016.md)。
- 本轮资源释放子项完成；唯一下一项仍是当前视角/两线程EV负载下同步分段定位，原门限保持。HW10未通过，不启动飞行。

## 当前交接：HW10-EV-015 / 010.3

- 普通有界新视角未武装复测已完成；用户指定范围为EV连续性/EKF融合，禁止控制、武装、飞行。主测250.519s，估计相对首条最大位移2.82cm（非真值误差），位置/高度观测拒绝均0，旧视角严重漂移未复现。
- 连续两条RTT>10ms使最近合格同步超过原2s，产生1.08s EV空窗及主EKF短暂停融；因此连续融合仍未通过。原门限、原版VINS、两线程及固件未改，本轮CPU未单独测量。
- 恢复完成：初末1095项零差异、EV_CTRL/MAG_TYPE原0/0，无参数待恢复；11213640字节ULog完整取得。自有进程停/.runtime空/rmem212992，Agent21640未重启；终态DDS新消息、未武装、输入publisher0。012历史待恢复问题已解除。
- 诊断NSH提示符解析已修复，主机/Nano各5项通过。014失败证据保留，不唯一归因视角。
- 唯一下一子项：当前视角/两线程EV负载下同样本同步分段诊断，区分Agent队列/处理和FC/UART；保持10ms/2s及其余门，不直接刷固件。HW10/HW08仍未完成，不能转飞行。
- 停止原因：本轮试验/分析/安全恢复完成，非父目标通过。证据[015](../evidence/hw10-ev-20261105-015.md)、[013/014](../evidence/hw10-ev-20261105-013.md)。

## 最新交接：HW10-STAGE-011 / 010.2

- 普通有界子项完成：原生阶段计时定位前端跟踪吞吐限制，并将硬件OpenCV线程1→2；特征数/数值算法/原门限/固件均未改，没有EV/控制/飞行。
- 同一诊断binary两组120s：跟踪中位116.446→82.220ms（-29.39%），估计/发布3.989→5.454Hz（+36.72%）；processImage约55–58ms、边缘化3–7ms、发布约1ms、锁等待约0.001ms。总CPU增加，不能外推完整EV/地图/EGO裕量。
- 原版安装binary恢复SHA98933…、vendor源码42ca…未动，保留配置2；原版新epoch再测120s，无窗口内锁定，优化接收约5.495Hz/最大332ms。所有propagated_receipt_stale均在测量结束后的清理阶段，原日志保留。
- 原生编译/基线重链接/计时实测通过，rig主机/ARM各4项、会话5项、安装16项一致；静态检查通过。自有感知/计时全停、rmem212992、.runtime空，Agent21640未重启，终态DDS新消息/未武装/输入publisher0。
- 唯一下一子项010.3：两线程下未武装EV/EKF全链路复验，保持0.615998s/10ms/2s门并核对CPU裕量；HW10/HW08保持未完成，不直接改固件调度。停止原因：本轮最小性能修复/地面回归交付，非连续融合或飞行通过。
- 证据[evidence/hw10-stage-20261105-011.md](../evidence/hw10-stage-20261105-011.md)，原始artifacts/runs/hw10-stage-20261105-011及相关三组-perception；大二进制/对象保留Nano同名目录。

## 最新交接：HW10-SYNC-010.1

- 普通有界时序诊断/未武装EV复验完成；原门限、生产算法和固件未改。第一轮EV284条/11.245s后telemetry接收龄0.618829s锁定；原生solver日志附近亦有0.729743s间隔，尚未唯一定位算法阶段或DDS接收。
- 首轮原生订阅启动插入失败，仅锁定后93条，不当作故障瞬间证据；复核提前预热采289条，接收最大0.533030s，无同次接收故障。快照四核93–94%@1479MHz，支持查Nano竞争，包含诊断负载，非唯一根因证明。
- 复核120s窗口：EV1902条/74.119s，最大间隔133ms；有效段实际RTT10385us未断流，009有效同步修复有实机正证据。但高度融合DDS旗标短暂关闭，ULog因USB掉线未取得，不能称三路持续融合或长时通过。009失效状态报告也已实测正确。
- 用户重连USB后两参数恢复0/0、logger已停、1095项与008备份零差异。USB随后仍掉线，待稳定补取SD日志；重连期DDS短窗口0消息，后续15s五类恢复/未武装/输入publisher0，Agent21640未重启。自有进程全停、rmem212992、.runtime空。
- 唯一下一子项010.2：原生跟踪/processImage/边缘化/发布阶段只读计时与线程占用，依结果选最小性能修复；保持门限，暂不改固件调度。HW10仍in_progress。
- 停止原因：两轮有界证据分界与限定复验交付，父功能未通过。证据[evidence/hw10-sync-20261105-010.md](../evidence/hw10-sync-20261105-010.md)。

## 最新交接：HW10-SYNC-009

- 已修共享有效同步缓存与EV当前状态诊断，10ms/2s门限未改；Nano构建并强制安装，16项源码内容一致。真实控制/EV本轮未启动。
- 169同步隔离回放：输出3390→4131，阻断838→97，剩余均为原2s过期，最大空窗仍2.08s；不宣称连续融合或飞行通过。
- 唯一下一项HW10-SYNC-010：查VINS遥测接收间隔并新epoch未武装EV复验；保持门限，不并行重负载回放，暂不改固件调度。HW10仍in_progress。
- 停止原因：代码修复/隔离回归子项交付；实机运行资格未通过。证据[009](../evidence/hw10-sync-20261105-009.md)。

## 最新交接：HW10-SYNC-008（2026-11-05）

- 普通有界审查/未武装验证子项完成；用户要求先保留10ms/2s等门限，检查EV连续性、EKF融合和RTT控制门控。本轮没有修改生产桥接器、门限或固件，原连续运行标准未通过。
- 代码与169条真实RTT隔离回放确认：最新高RTT覆盖此前同步，EV/Offboard/设定点各838次输出机会被挡，最大3.08s空窗；未武装预发送也会回到DISABLED。控制仅内存调用，真实端无控制消息。
- 第一轮真实178.39s：EV947条/首末38.49s；10017us RTT期间定位22条全valid，却产生1.0918s EV空窗；ULog主EKF1的EV位置/高度/yaw旗标关闭后恢复。之后telemetry_receipt_stale锁定，EV长期停发；detail仍显示旧ev_only，是另一诊断缺陷。
- 首轮并行隔离回放带入额外Nano负载，已明确该干扰。第二轮新epoch去掉并行回放/测试，仍在telemetry接收龄0.619828s超过原0.615998s门时锁定，IMU/传播仍新鲜；不能全部归于回放，也没有唯一定位到VINS生产/传输/调度根因。第二轮EV仅2.304s，不能算长时通过。ULog原配置缺EV aid逐样本，复核有dropout，保留覆盖限制。
- 现场确认已拆桨/固定/稳定供电。临时EKF2_EV_CTRL0→11、MAG_TYPE0→6用于独立地面航向参考与EV，双轮后已恢复；最终1095项与开工完整回读零差异。两轮始终未武装/真实端仅EV发布者；收尾所有自有感知/EV/观察器退出、rmem恢复212992、fmu/in publisher0，用户Agent21640 active/NRestarts0保留。
- HW10/HW08保持未完成。唯一下一子项HW10-SYNC-009：共享最近合格同步健康与EV状态新鲜度最小修复/回归；坏RTT不刷新有效同步，原10ms准入/2s到期及clock/epoch门保留。VINS遥测间隔问题独立保留；先修桥接器与定位源，再决定是否需要固件调度，不直接刷写。
- 停止原因：所要求审查/两轮有界验证/具体修复决策完成，非运行资格通过。证据[evidence/hw10-sync-20261105-008.md](../evidence/hw10-sync-20261105-008.md)，原始artifacts/runs/hw10-sync-20261105-008及-repeat。

## 最新交接：DDS-LATENCY-007（2026-11-05）

- 普通模式有界诊断完成，范围仅TELEM1 DDS，无EV/控制/飞行，不改10ms/2s门。USB重插恢复，真实未武装1095项完整回读通过；相对005仅预期SER_TEL1_BAUD2M→1M，006参数复核缺口已补齐。
- 原生同样本匹配80个：Agent完整读到→完整写出中位0.222ms；15个高RTT样本Agent段中位0.199ms，主要延迟在其外。原生记录尾部/未刷出缓冲覆盖限制如实保留，不能推定全部样本。
- CH340短包位写请求成功但未通过读回检查；120s仍21/119 RTT>10ms，否定试验未永久启用。随后usbmon完整回复（含尾URB）59样本，11个高RTT样本USB完整OUT交付仅0.085–0.116ms。剩余转换器UART/FC调度仍未完全分离；FC top快照idle2.9%、三INS队列合约35%，是下一候选，非唯一根因证明。
- 用户只有当前CH340，无另一适配器对照。本轮没有更改飞控估计器/传感器/机型/遥测流率，未刷固件。失败helper移入artifacts，不留生产工具；原生临时override删除、usbmon读者退出/模块卸载。原6fc2修复库/1M/v4服务唯一Agent21640，NRestarts0；30s恢复回读五类正常、未武装/输入publisher0。
- HW10/HW08保持未完成，严格RTT门不标通过。唯一下一子项：先核对当前实际PX4固件构建基线，在保留传感器/EKF与门限前提下准备可审查的DDS任务调度候选及资源验证方案；不直接刷写、不继续无依据串口调参。
- 停止原因：本轮分段定位与单变量否定试验完成；缺物理对照/已验证在线调度调整路径，不扩大到估计器删减或固件部署。证据[evidence/dds-latency-20261105-007.md](../evidence/dds-latency-20261105-007.md)，原始artifacts/runs/dds-latency-20261105-007。

## 最新交接：DDS-LATENCY-006（2026-11-05）

- 普通模式，两轮探索完成；用户范围为继续修TELEM1 DDS，不启EV/控制/飞行。Agent帧重同步缺陷已修；严格RTT准入仍未全过，父HW10/HW08不标passed。
- 原版遇异常帧后丢弃后续正确帧：同包重放28181帧/88ping→补丁30521帧/95ping，恢复具体漏答事件。补丁0002仅硬件配置，保留CRC检查；32组主机/ARM实际断言通过，原版失败。只读基线重链接逐字节复现cb802...后单对象替换，最终库6fc2ac97...；原源目录及/usr/local未改。
- 第一轮补丁+2M仍有约1s空窗；第二轮新CRC异常证据下退1M，抓包中异常716→6且无>0.3s串口有效帧间隔，尚不能将原因确定为CH340硬件/驱动。
- 最终1M+补丁180.007s无strace：26026条，姿态/位置最大间隔162/180ms、同步1.031s；RTT中位7.477/P95 11.987/最大17.697ms，33/169>10ms。无时间倒退，状态均未武装，fmu/in publisher0。本窗口未见旧约1s姿态/位置停顿，不是完整EV/控制资格。
- FC波特率1M已save/readback并维护重启ACK0；Nano永久服务1M/v4、局部LD_LIBRARY_PATH隔离修复库，唯一Agent17888、临时override删除。最终完整USB参数probe因电脑无ttyACM而ENOENT，Nano也无FC USB；用户明确没操作；内核14:38:32记录异常USB disconnect（不同于14:37:13授权维护重启），未再枚举，原因未定。已请求只重新插紧电脑端USB，不碰TELEM1；不能称最终1095项零差异回读。随后10s收尾DDS五类新消息仍到达、未武装，保留服务，不盲目重启。
- 唯一下一子项：USB恢复后先补最终参数回读，再固定当前1M+补丁，针对同一超10ms样本分离串行往返与Agent处理/调度时长；新证据后才调整调度/流量，不扫速率或重复无假设实验。未启动EV/NED运动或控制。
- 停止原因：普通模式两轮探索到限，严格RTT仍未过/末次参数复核缺USB；证据[evidence/dds-latency-20261105-006.md](../evidence/dds-latency-20261105-006.md)，原始artifacts/runs/dds-latency-20261105-006。最新配置config/hardware/px4_telem1_dds.json。

## 最新交接：DDS-LATENCY-005（2026-11-05）

- 普通模式，用户范围为USB电脑+UART Nano条件下修DDS时效；两轮速率探索完成，未启动EV/控制/飞行。父HW10保持in_progress，严格时效尚未全过。
- 实际端口确认：PX4 d6f12ad1/1.17.0，UXRCE_DDS_CFG101，ttyS1/TELEM1，USB SYS_USB_AUTO2。FC公开1095项前后唯一变化SER_TEL1_BAUD115200→2000000，已save/维护重启生效；两次重启ACK0、未武装。未运行历史易阻塞runtime stop。
- 1M60s：RTT中位7.274ms/最大25.196ms、12/49超10ms；2M75s：中位4.841ms/P95 9.509ms/最大18.244ms、4/65超10ms。2M姿态/位置最大空窗仍1.031/1.063s，同步2.038s；主延迟改善但不能判完整通过。完整数据取代先前短窗口描述。
- 2M候选已持久保存到FC和Nano systemd，服务源config/hardware/microxrce-agent.service、配置config/hardware/px4_telem1_dds.json；唯一Agent12938 active/enabled，临时override删除。旧px4_dds.json是历史USB方案。本轮观察器已退出、无EV/控制publisher，USB保留电脑。
- 唯一下一子项：固定2M版本，关联同一尖峰事件的PX4 cycle/同步重试与Nano USB/Agent收发时刻，定位约1s停顿；不重复无假设重启或继续升速。之后才恢复未武装EV/NED及运动验证，HW08装机/RC/控制依赖保持未完成。
- 停止原因：普通模式两轮探索上限，严格时效未全过。证据[evidence/dds-latency-20261105-005.md](../evidence/dds-latency-20261105-005.md)，原始artifacts/runs/dds-latency-20261105-005。未宣称整机冷启动/融合/飞行资格。

## 最新交接：DDS-LATENCY-004（2026-11-05）

- 普通模式，用户授权修复DDS时效；本轮仅日志单变量，未启EV/控制/飞行、不改FC参数/速率/门限。修复尚未完成。
- baseline30秒timesync RTT83–139ms/最大空窗2.045s；唯一v2 Agent稳定30秒末RTT132ms/最大空窗2.037s，日志假设未解决。初次测试因systemd自动拉起原Agent发生短时争用，检测后退出测试实例，该窗口作废。后续统一通过systemd临时override验证。
- 已删除临时override并恢复原v4/115200自动服务，唯一Agent11513；恢复后45秒观察五类消息全部恢复，观察器退出0，输入publisher0。没有永久源码/配置改动。用户未接电脑也可维护：USB接Nano即可；当前仅DDS UART，不能可靠读改FC速率/启动参数。
- 唯一下一项：取得独立USB维护通道，回读真实TELEM1配置及client吞吐，再做单变量速率/流量验证。不能只改Nano波特率或放宽门限。等待用户接线；HW10/HW08保持未完成。
- 证据[evidence/dds-latency-20261105-004.md](../evidence/dds-latency-20261105-004.md)，产物artifacts/runs/dds-latency-20261105-004。停止原因：外部条件，缺FC配置通道；非修复通过。

## 最新有效交接：2026-11-05 DDS-CHECK-003

- 用户现场纠正：当前DDS接飞控TELEM1，另一个TELEM口未使用；本次未回读飞控端口参数。
- 执行模式：普通只读检查；用户范围为“DDS已调好，检查并汇报后续任务”，不自动延续旧修复Goal，不启EV/控制/飞行。以下旧故障条目为历史，不再作为当前无DDS消息的结论。
- 已确认：Nano可达，用户Agent7950通过CH340 ttyUSB0以115200运行。现有Agent上30.016s只读观察收到五类真实遥测609条，时间戳0倒退、38个fmu/in话题publisher均空；DDS接收已通，旧零消息阻塞解除。观察器退出，用户Agent保留，未改参数/重启。
- 未解：Timesync RTT81–135ms、最大间隔4.036s，超过现有EV门10ms/2s，当前链路尚不能直接恢复EV。最后xy_valid=false/heading_good_for_control=false、EV融合false。当前Agent在/usr/local并链接FastDDS2.14.7/FastCDR2.2.8，与旧锁定隔离组合不同；旧USB临时切换配置不代表新TELEM1配置。
- 父目标HW10仍in_progress；已完成历史静态融合、SDK时间候选、guarded NED代码与隔离检查。未完成真实NED配准、运动方向/尺度、独立VINS断源和控制/接管/退出。HW08严格刚性安装与含桨包络仍未通过，rig control_usable=false；上次无RC事实本轮未重新核实。
- 唯一下一子项：HW10 TELEM1时效核对，固定当前双端配置/版本/启动方式并定位RTT与空窗，通过原门后再恢复未武装EV/NED及方向尺度验证；真实控制需HW08/遥控接管条件。随后HW11悬停→HW12短目标→HW13障碍→HW14交接。
- 停止原因：本轮检查与汇报完成。证据[只读复核](../evidence/px4-dds-recheck-20261105.md)，产物artifacts/runs/px4-dds-recheck-20261105-003；没有启动下一项。

- 修复现场最新：用户称已重启，FC USB重新接入但当前被QGC PID8957独占，诊断打开返回EBUSY；内核曾枚举bootloader，尚不知用户是否刷固件，已询问，未关闭/抢占QGC。Nano ttyUSB0暂未识别。当前不发送新命令，等待QGC状态及两条线重接确认；115200参数仍未执行。


## 活动修复范围 2026-11-05 TELEM2 DDS调通为止

- 用户明确开始调试、调通为止，Goal完成模式（不创建自动Goal）。USB MAVLink为维护通道，TELEM2 DDS，禁止EV/控制。第一方案仅运行时115200，不改永久参数。
- 实际向FC发送uxrce_dds_client stop，10s没有完成回显，未发送start/波特率变更；随后USB心跳4s也未收到。当前维护通道失响应，不能宣布降速已执行或已修复。代码/日志artifacts/runs/telem2-dds-fix-20261105-01。
- 已请求用户完整断开全部供电并重接、保留两条数据线。唯一下一动作：恢复USB心跳后避开runtime stop，改为SER_TEL2_BAUD测试值回读+一次维护重启；测试阶段不启EV/控制。永久原值921600已知，需记录差异和终态。等待用户“已完整重启”。


## 最新确认 2026-11-05 TELEM2独立DDS

- 用户新增CH340 UART，Nano /dev/ttyUSB0。Agent921600只读20s，ROS计数空；采样有错误XRCE式字节，DDS尚未接通。所有本轮Agent/订阅已退出，不发EV/控制、不改参数/重启。
- FC USB接PC后MAVLink正常，参数完整1101项；实际SER_TEL2_BAUD921600、UXRCE_DDS_CFG102、MAV_1_CONFIG0、SYS_USB_AUTO2。启动日志证实DDS在ttyS2@921600，Running disconnected；旧extras不存在。新状态取代下方旧USB故障/缺串口线事实。
- 唯一下一项：针对TELEM2→CH340→Nano速率/驱动/电平/接线做单变量验证；可在明确实施范围后双端降速。本轮只读验证结束、HW10未通过。旧config/hardware/px4_dds.json与USB切换入口尚未迁成新双通道，禁止直接套用。证据[evidence/telem2-dds-20261105.md](../evidence/telem2-dds-20261105.md)。


- TELEM2检查最新交接：用户已称USB接运行Codex本机，但本机lsusb/sysfs无26ac设备、无ttyACM，最近内核仅USB3-2断开事件；Nano也无FC USB，仅CH340 ttyUSB0。已请求保留TELEM2并将USB重插本机另一口，等待设备枚举后只读实际参数。当前UART有错误字节、DDS未建立，不修改FC参数、不继续猜测波特率。

- 2026-11-05 Nano已开机，ssh jetson可用；新boot b8e9f707...，新增CH340串口/dev/ttyUSB0。用户TELEM2 DDS波特率未知。只读921600 Agent+观察器20s计数空，已退出。被动常见波特率扫描有字节，约1M附近呈XRCE结构但帧头/数据错误，未建立DDS；不能报告连通。无FC参数/重启/EV/控制。已请求保留TELEM2并将USB接PC，以只读获取SER_TEL2_BAUD/UXRCE_DDS_CFG，等待用户；不再猜测扫描。产物artifacts/runs/telem2-dds-20261105-01。

- 2026-11-05用户报告已新增TELEM2→Nano串口并配置DDS（非MAVLink），尚待实测，不再沿用“无第二串口线”的现场事实。请求只读验证。直接SSH地址和`ssh jetson`均指向192.168.31.186、返回No route to host；当前尚未接触Nano/FC，DDS状态未知。唯一下一步：确认Nano当前网络/IP，连通后检查串口/Agent并订阅遥测，不改参数或发EV/控制。

- 用户最新明确不需要备份：后续恢复跳过备份，不再以备份为执行前置；仍需取得microSD读写通道，才能写入已准备的恢复extras。目前USB无回包，实际恢复未完成，不因此清空参数或刷固件。

- 最新用户要求切回MAVLink复测：Nano115200/2000000有界发现均RX0，后一组发送超时；没有成功执行飞控端切换，不报告已切回。无Agent/EV/控制/重启，诊断已关闭。已准备artifacts/runs/mavlink-restore-check-20261104-01/recovery/extras.txt，bash -n通过但未写FC；下一步需microSD读卡器备份日志/替换自有hook再恢复。证据evidence/mavlink-restore-check-20261104.md。

- 最新直接DDS实测（用户指定）：Nano串口独占，Agent921600配置成功，30s strace无USB数据read/write；订阅器初次库环境冲突已纠正，独立ROS环境15s定时器正常、DDS遥测计数0，退出0。Agent/订阅器已停、串口释放；没有改PX4参数/重启/EV/控制。见evidence/dds-direct-20261104.md。直接DDS也未连接，尚未修复，不能诊断为硬件损坏。

- 最新单USB互斥审查：原切换脚本stop DDS后未验证退出就启动MAVLink，存在争用缺口。本地生成器已加status guard，DDS仍运行则退出并保留hook，三个定向测试通过；尚未写FC或再次运行。当前板端是否争用未知，不能仅凭无MAVLink心跳诊断故障；此前纯DDS/raw测试亦RX0。仍需SD读取启动日志与恢复。

- 最新Nano复测：用户接回Nano、仅USB供电；26ac:0032/1-2.4可枚举，无占口。主机发送MAVLink操作成功但RX0；DTR/RTS五组合及只读ver all均无回复。未改参数/重启/EV，诊断已退出。不能认定硬件损坏或恢复；下一步需microSD日志与撤销临时启动hook，当前缺读卡器通道，不重复串口试探。见evidence/fc-condition-20261104.md。

- 最新连接诊断：用户确认当前仅USB供电，之前曾接14V（接口/降压未知）。PC应用USB26ac:0032可枚举；被动12s与主动MAVLink身份发现均RX0/无心跳。不能据此诊断硬件已坏或正常，参数恢复仍未回读。证据[evidence/fc-condition-20261104.md](../evidence/fc-condition-20261104.md)。当前无诊断进程占口；后续先确认14V接法、读取SD启动日志，不再盲目切DDS。

## 当前活动：HW10 DDS修复模式，等待读取FC端启动日志

- 用户明确要求修好再结束；本轮继续到实测修复，不将诊断当通过。已接回Nano，stable MAVLink完整探针通过；首次探针因bootloader→app枚举间隙端口不存在失败，稳定后通过。
- 同一Agent+strace在真实MAVLink端口能读数据；PTY协议响应此前3/3通过。新增唯一受控hw10t60s纯传输试验：只改SYS_USB_AUTO0，set+e脚本/原生备份回读，未改MAG；维护重启ACK0后pyserial↔PTY Agent双向抓取32s，USB RX/TX均0，未启动VINS/EV/控制。
- 60s恢复窗口后Nano两次被动探针及主动发现仍无RX；单独FC USBDEVFS_RESET也未恢复。不能确认当前SYS2/hook恢复，等待真实回读；不得引用历史恢复结果。Nano此时无Agent/EV/代理活动。
- 用户已换口，路径1-2.1→1-2.4，内核记录bootloader→应用重启，MAVLink探针仍无HB；未进行新DDS配置。当前唯一外部动作：USB接PC取hw10t启动/恢复日志，并确认是否USB以外独立供电/拔线灯灭；已发async，等待答复。当前参数/hook仍未回读。产物artifacts/runs/hw10-dds-fix-20261104-01（双端已保存）。

## 当前：HW10 DDS只读排查，根因未闭合

- 用户要求继续排查，FC保持电脑MAVLink、原参数不改；无DDS切换/重启/EV。两类Agent145B日志不能区分会话成功；最新窗口正常USB枚举，不能拿早期枚举错误直接解释本次失败。
- Nano同一Agent做PTY隔离重放真实协议帧，3次回复共129B，已退出；只证明二进制/帧响应可运行，不代表真实USB DDS通过。证据[evidence/hw10-dds-audit-20261104.md](../evidence/hw10-dds-audit-20261104.md)。
- 唯一下一项：不改飞控参数的Nano MAVLink基线CDC/termios及原始收发量测，再决定DDS受控验证；当前FC在PC，尚不能量测Nano真实USB。HW10保持in_progress，双串口待线、控制待RC，暂停重复协议切换。

## 当前：HW10r电脑端恢复完成；暂停USB DDS切换

- 用户已把FC接回电脑。被动观察577.393s后收到真实未武装PX4心跳；probe/verify退出0，SYS_USB_AUTO2、EKF2_MAG_TYPE5、EKF2_MAG_CHECK0，hook不存在、DDS停止；原生BSON与hw10r before完全一致。
- 一次未武装维护重启ACK0后probe再次退出0，1098参数完整、三项仍2/5/0。QGC已重开，当前FC USB留在电脑；Nano本轮Agent/EV/观察器已停，VINS未启动、EV0。
- MAVLink恢复已完成，DDS根因尚未解决。唯一下一子项：仅查清Nano DDS通信路径；在新证据/可靠方案前不再次切换USB协议，不重复同类重启。第二串口仍缺线，无RC，不做控制。
- 产物artifacts/runs/hw10r-pc-recovery-20261104-01，过程见changes/2026-11-04-017-hw10-resume.md。故障前独立窗口589.999507s/三类1178融合0拒绝已经补齐；动态/NED/控制未通过，HW10保持in_progress。

## 当前：HW10 飞控恢复及Nano回接确认完成 2026-11-04

- 原HW10 goal_completion仍未完成；用户最新收窄为“先恢复飞控”，本轮限定恢复出口完成。唯一下一子项：待后续继续HW10.3d余项；本轮不自动重启DDS/EV。双串口改造延期，需第二线及实物端口核对。
- 已确认：用户直连PC后，既有DDS会话在被动观察687.300s后恢复真实PX4 MAVLink。三参数回读SYS_USB_AUTO2、EKF2_MAG_TYPE5、EKF2_MAG_CHECK0；本项目extras hook已删除、DDS已停止。再执行一次fresh未武装维护重启ACK0，正常MAVLink启动、参数/hook/DDS再次回读通过。
- 原生参数备份/恢复后/重启后逐字节一致，2575B、SHA88f277bbf3d5c9d010f33dac7b52ff3c3ff13c983448d2cba34ee2339f42bdc5。重启公开参数1106→1098，仅8个DDS参数不再公开，共同参数无变化；原生存储完全一致。5/0为恢复原配置，不是飞行参数推荐。
- 本轮诊断全部退出，Nano无项目Agent/桥/相机/VINS匹配进程，.runtime空、rmem212992；QGC已重新打开PID44416；用户随后将FC USB接回Nano，PC QGC当前不再直连飞控。Nano只读probe退出0：实际system1/component1未武装心跳，1098/1098参数与PC重启后记录完全一致，三项仍2/5/0，DDS未运行；诊断后串口无占用。回接产物artifacts/runs/hw10-fc-nano-return-20261104-01。保留RViz仅历史画面，无实时定位/EV/控制。证据：[恢复报告](../evidence/hw10-fc-recovery-20261104.md)，产物artifacts/runs/hw10-fc-recovery-20261104-01。
- 旧脚本缺set+e为潜在恢复缺陷，本地生成器与失败注入回归已补；板上旧脚本未更新，本轮hook已移除。本次已实际恢复，不能再称当前飞控通信受阻，也未证实先前卡在哪条命令。先前Nano枚举/无通信根因未全部定位。
- 已有HW10基础：SDK候选315cb61b...300s稳态无>1ms未来戳、perception333.495s/325条有效；传播EV/30Hz限频、guarded NED代码与ARM隔离测试完成。hw10c历史未武装长窗口708.997s（含首个INT需另分离）、ULog融合/0拒绝、Agent TERM断链恢复有证据；详见[HW10过程](../changes/2026-11-04-015-hw10-completion.md)。
- 未解：新NED真实配准、运动方向/尺度、独立VINS断源、控制/接管及HW08装机出口。无RC、rig仍UNMEASURED/control_usable=false，HW10保持in_progress；本轮只恢复通信和原参数。停止原因：用户限定恢复任务完成。

## 地面站 GS01 软件部署完成 2026-11-04

- 用户授权配置work@192.168.31.223。普通模式有界部署，Debian13保留；专用Jazzy容器/项目消息接口、到Nano的专用SSH密钥、桌面五入口、ROS原生远程命令与QGC5.0.8已安装。路径/home/work/D435i-groundstation；操作见[地面站手册](../../docs/groundstation-debian.md)，证据[GS01](../evidence/gs01-debian-20261104.md)。没有保存密码、迁移第三方算法或改变飞控参数。
- 构建/导入、RViz OpenGL4.6、QGC界面启动、主机命令边界/只收遥测测试、地图字节/epoch校验及Foxy→真实SSH→Jazzy合成地图解码通过。直接跨版本DDS只发现话题，两个收包探针超时；最终路径改为SSH，不作为运行通过。没有真实有效定位/地图/规划或飞控连接资格，语音后端告警保留。
- 本轮地面站view/map/QGC测试均已退出，Nano地图relay377143已退出；没有停止/重启现有硬件会话，没有接触相机或发EV/控制。旧Nano会话退出/日志bad_alloc仅记录观察，原因不归于本部署；当前HW10.3b诊断与其已有状态保持，不清理其state/rmem。
- 停止原因：GS01软件部署与限定检查完成。无待执行地面站安装子项；下一硬件子项仍由下节HW10.3b维护。有效实时地图/完整特征视图/双向MAVLink需对应链路运行后验证，不自动启动。


## 当前交接 HW10.3b 2026-11-04

- 本轮同帧SDK诊断子项完成，父HW10仍in_progress。两次180s独立相机采集，无ROS/EV/控制/飞控改动。未带观察点稳态gyro1024/34848帧超前>1ms，最大4.50976ms；带观察点同帧确认SDK把递增硬件时间转换到系统时间后可超前18.620815ms（启动阶段），不是仅adapter/RViz/PX4制造。带观察点首5s后无>1ms，未当修复通过。[证据](../evidence/hw103b-clock-20261104.md)。
- tools/diagnostics/realsense_clock_probe只读相机诊断/仅进程内观察库，固定SDK基准与许可记录；生产库/来源源码不改。新增精确同戳分析及定向测试通过，ARM实际构建/采集、结构/diff检查通过。
- 已清理：旧统一stop发现过期下层state，先核对全部旧PID/组无活进程后归档清理并正常恢复rmem212992。两个探针均结束、五流关闭、global time1/emitter0回读恢复，.runtime空，无VINS/相机/relay/探针残留。PC view已停，RViz仅最后画面，当前非实时；不自动重启。
- 唯一下一子项HW10.3c：同版观察time_diff_keeper的USB请求start/finish、device_time/最短延迟和拟合输入，验证何种更新前移转换，再给出保持完整性门限的修复。当前未修改1ms检查，未改now/加常量延迟；具体拟合内部原因及生产修复尚未完成。
- 真实EV运动方向尺度仍未验证；后续控制/接管仍需遥控器，HW08严格装机缺口保留。停止原因：同帧诊断出口完成，非HW10整体通过。

## 历史诊断 HW10.3a 2026-11-04

- 本轮按有界时序诊断子项实施；父HW10仍未完成。用户继续HW10.3，复用历史故障/ULog并追加一次现有会话120秒只读native采集，无EV/Agent/控制/参数或门限修改，无运动/飞行。产物[证据](../evidence/hw103-timing-20261104.md)。
- 已确认：同一个IMU source_stamp=1792456844267253760，在独立native接收时超前3.311778ms，adapter接收时超前1.124747ms，检查时超前1.013653ms并锁定。不是PX4/RViz产生；不是仅adapter取时误差。当前118.159s实际样本22875条，239条超前>1ms，最大4.08112ms；系统与单调时钟偏差全段变化0.677微秒，不支持系统时钟跳变解释。
- 源代码追踪：统一IMU沿用gyro经SDK转换的时间；global_time_enabled下设备→系统拟合无“不得超前”保证。已定位到上游源时间映射层，具体设备原生时间/SDK拟合输入尚未同帧记录，不能宣称已修复或唯一证明拟合系数为根因。1ms门限保持，禁止改now/偏移常数掩盖。
- 新增分析脚本及定向回归通过，旧951.257s native去掉首5秒仍154条超前>1ms、最大2.269994ms，独立复现。当前native已正常SIGINT退出（timeout124为预定结束），无诊断进程残留。
- 既有hardware-fastview-20261104-02已触发imu_future_source_stamp，RViz应为INVALID；不把保留窗口当有效定位，不自动重启。相机/只读relay/VINS仍按先前查看请求保留；停止见下节，结束需恢复rmem212992。当前未运行EV/控制。
- 时序根因尚未全部闭合；下一子项HW10.3b：记录同一运动帧的硬件/SDK映射时间与主机到达时间，核对设备时域转换/拟合误差，再提出保持完整性检查的修复；在此之前不进入真实EV运动方向尺度验证。遥控器仍是后续控制/接管前提。

## 历史实时特征视图 2026-11-04

- 本轮VIS12，普通模式；用户同意降低显示延迟。图像独立JPEG预览通道，geometry独立通道，两端最新帧覆盖；机体轴/TF取传播位姿，优化结果仍为轨迹。仅可视化，无Agent/EV/控制/参数或算法门限变更。
- 已确认：hardware-fastview-20261104-02，epoch8cc66234464241119df05b6792e3cea7；59.75s显示观察150/150有效，body9.72Hz、image3.41Hz、current points4.79Hz、camera4.82Hz、history1.72Hz，解码错误0。源到PC中位body65ms/image378ms，P95约350/929ms，仍有抖动，非屏幕端到端保证。见[证据](../evidence/vins-fastview-20261104.md)。
- PC view17163/RViz17370，PID文件artifacts/runs/hardware-fastview-20261104-02/{view,rviz}.pid；Nano relay geometry368538/image368537均由统一session接管。保留实时窗口，活动rmem8388608；健康快照仍在artifacts/runs/hw09-live-view-20261104/live-status.json。
- 旧visuals01已正常停止（停机阶段有imu_future_source_stamp，既有时序风险保留），rmem恢复212992。首次fastview01在相机检查脚本141失败，未启动VINS；修复两处awk提前退出的pipefail风险，相关大输入回归通过，等待relay已清理，再启动02。没有无假设重启VINS。
- 完成后保留实时显示；结束先SIGINT本轮PC view/RViz，再Nano bash tools/hardware.sh stop，确认两个relay和定位/传感器退出，rmem恢复212992。显示失效不自动重启、不放宽健康门限。
- VIS12短观察时有效；后续HW10.3a采集中已出现时序锁定，当前以本页顶部状态为准。HW08严格装机/长期稳定/飞控资格缺口保留。

## HW10 部分完成并收尾 2026-11-04

- Goal完成模式；用户授权跳过HW08，现场已拆桨/供电正常，无遥控器。本轮仅未武装EV；HW10和HW08均in_progress，不进入HW11。
- 已确认：高频传播里程计→同一桥EV-only→真实PX4静态融合打通。最终epoch993239d311bb44c0bec8d7700f54cf80约47s、1251条EV；ULog主实例0位置/高度/yaw aid各94样本fused、拒绝0，始终未武装。板上近似仅显式开关使用，rig仍UNMEASURED/control_usable=false。
- 代码：EV-only最多30Hz、raw先限频后反序列化，保留优化健康和原采样时间；Agent/观察器/EV先预热再启动VINS。默认未测rig0EV与隔离节点通过；真实control模式还需统一传播EV源后验证。
- 未闭合：旧/新会话均出现过约1.1–1.2ms IMU未来戳；冷启动竞争出现接收/图像源龄锁定，最终静态窗口内有效但窗口后再触发未来戳。未放宽这些门。未做运动方向/尺度、人工接管/控制/退出或首飞配置资格。
- 已收尾：原1098参数零差异，native BSON前后一致，SYS_USB_AUTO=2、DDS停止、hook删除；相机/VINS/定位/EV/Agent/观察器退出，.runtime空、USB无占用、rmem212992。PC RViz仅保留最后画面，实时视图节点已停。
- 停止原因：外部条件（无遥控器阻塞控制/接管出口）；其余未完成事实保留。唯一下一子项HW10.3时序根因与未武装方向尺度验证，先读取本轮故障快照/ULog，不重复无假设冷启动；控制专项等现场具备遥控器再执行。结果：[HW10证据](../evidence/hw10-ev-static-20261104.md)。

## 历史只读可视化会话 2026-11-04（已由HW10收尾）

- 用户要求RViz查看真实VINS轨迹和PX4位姿；已启动Nano perception会话hw09-live-view-20261104，epoch8eb97b06957d44d487b8494fc97b4a71。PC Humble RViz保持打开，1Hz既有定位日志生成青色轨迹，无新增Nano ROS订阅/控制。
- 用户确认供电并重新插拔飞控USB后恢复只读MAVLink；PX4 estimator flags=129，位置无有效标志，当前仅显示橙色姿态。两局部世界未配准，橙色显示平移+3m用于分区，不可作为两者误差。未发送EV/控制或改参数，融合未验证。
- 用户查看期间保留相机/VINS/定位、PC视图/串口监听/RViz；PID位于artifacts/runs/hw09-live-view-20261104/{view,rviz}.pid，Nano由tools/hardware.sh status/stop管理。结束查看时先停本地视图/串口，再停Nano会话恢复rmem212992；不得混入下一运行。
- [显示记录](../changes/2026-11-04-003-hardware-live-rviz.md)。当前不开展HW10；真实融合位姿仍需HW08装机复测与HW10融合联调。

## HW09 完成 2026-11-04

- 执行模式：Goal完成模式；用户明确允许HW09跳过HW08装机依赖，后明确取消optimized/telemetry的0.868306s源龄否决。HW08仍in_progress，装机后复测；其余门保留。
- HW09限定地面出口通过：统一分层入口/会话PID日志/status/stop，同一桥compute_only不创建任何PX4发布者/enable服务。真实rig仍未测，仅隔离计算使用板上候选。操作见[hardware-running](../../docs/hardware-running.md)。
- fresh epoch 5d4c9095f03a43c6809ff938babf489c，300.020s有效完整负载：12/12计算目标、12曲线，定位/map无失效；优化5.47Hz/传播180.63Hz，源龄最大0.608s，队列峰值2、有效窗口丢弃增加4且无持续增长。CPU处理进程合计P95约329%/四核400%，CPU最高36.5°C。静止相机+真实规划负载，非实际移动/飞行资格。
- 定向构建/安装内容核对、源龄/会话/坐标时间回归、域83隔离节点通过；旧日历mtime安装跳过与僵尸stop问题已修复。报告保留run01/02失败、区间分位数和观察器health空窗等局限：[HW09证据](../evidence/hw09-full-load-20261104.md)。
- 终态：本会话全部停止，停止VINS后失效已观察，.runtime为空、无项目处理进程残留，rmem恢复212992；无真实EV/控制/参数写入/武装/飞行。停止原因：HW09限定出口完成。
- 唯一下一项：HW10前置核对。恢复需装机后复测HW08，并由现场确认拆桨、供电稳定和遥控可用；本轮不自动执行HW10。初步300s/约1m/0.10–0.15m/s仅计算候选，融合和实飞预算待后续冻结。

## 实机迁移规划与实施 2026-11-03

- 执行模式：本轮Goal完成范围为HW08前三项；用户最终确认板子会弯曲、没有硬底座，接受“这一块差不多即可”。已完成该调整范围的板上近似候选/采集证据/同桥control软件验证并收口。**原HW08严格安装出口未通过，父模块仍in_progress，不自动转HW09或真实EV/控制。**
- 唯一下一项：HW08最终刚性安装、重新量测变换与含桨包络，再验证真实配准/安装误差。当前近似在rig.json的bench_observation.approximate_transform；T_airframe_imu仍null，control_usable=false。恢复严格实测需要刚性共同底座或最终机架；本轮不继续要求用户重复柔性板动作。
- 采集结果：工作站解码+Nano轻量转发、OpenCV单线程的run09/10有效跨度377.35/415.45s，动作期无锁定，日志最大优化源龄约0.694s。opencv_threads=1已入硬件配置和session哈希绑定。run11新增原生订阅负载仍源龄失效，不能保证新增订阅/满载稳定；全部门限保持，1ms仅为此前获授权相机IMU候选。
- 安装结论：两静止训练姿态相机/FC重力方向变化9.80°/7.45°；独立侧倾残差3.16°，严格固定旋转未通过。用户接受平均近似：沿用前0.20/右0.01/高0m芯片端点量测（重新固定后未复量），相对yaw按用户前向平行声明，roll/pitch修正3.293°/1.611°；拟合各静止残差0.22–3.15°。该候选所有四段参与拟合，无独立通过，未提升为真实airframe外参。
- 软件结果：同一Px4BridgeNode复用OffboardSupervisor硬件control，完整姿态换算后配准yaw/原点，保留源/接收龄与时钟/epoch故障门控；yaw-only规划杆臂仍为低倾角候选，实测姿态下几何差最大约3.69cm，非外部跟踪误差。85项主机定向、ARM bridge构建及7安装模块哈希一致；域83使用近似数值的合成输入1164EV、显式enable后40mode/40setpoint/1模式请求，enable前控制0；EV-only真实未测rig0EV、三个control publisher0，合成518EV后epoch锁定。
- 终态：所属相机/VINS/原生诊断/串口转发/隔离节点全部退出，.runtime为空，USB无主机占用，rmem恢复212992。真实FC只读MAVLink，无Agent、真实EV/控制/模式/武装/飞行、无参数写入。结果：[板上证据](../evidence/hw08-board-20261103.md)、[control变更](../changes/2026-11-03-009-hw08-control-bench-candidate.md)。
- HW07通过范围：实际PX4 1.17.0/d6f12ad1、FMUv5与锁定msgs一致，隔离ARM Agent2.4.3/FastDDS2.14/FastCDR2.2构建和真实60.005秒DDS回读通过。status118、att5940、local_position3000、timesync/EKFflags各60，时间戳零倒退；38个fmu/in话题publisher合计0。未解锁/无EV/控制/飞行/刷机。
- HW07终态：一次性开机DDS结束，SYS_USB_AUTO 2→0→2已保存恢复，extras钩子已删除，USB onboard MAVLink恢复、DDS停止；原1098参数零变更，新增8个可见DDS默认项，原生前后BSON逐字节相同。Agent/观察器/诊断退出、主机串口无占用、ROS图无fmu话题。仅保留dialout访问权限与隔离安装；全部证据在artifacts/runs/hw07-usb-20261103-01。
- HW07边界：在线MAVLink stop路径失败未资格化；原Hexa X机型配置待实际机体核对，本地位置/速度有效位false、未EV融合，不能据此飞行。Nano日历旧值未改，DDS已映射Nano系统epoch，不可重复加减offset；HW08继续发送时间验证。诊断阻塞/首个零数据窗口及两次用户断电恢复均保留。
- HW06通过范围：真实rig/odometry/depth→唯一EGO地图/规划→traj_server→compute_only action，实际零PX4控制publisher；侧向0.9m目标、替换/取消/匹配ABORT、实物阻挡三维目标、新epoch清图/旧查询拒绝/无自动goal有证据。没有真实移动或到达成功。
- 实物：镜头前端到障碍正面50cm，高42/宽22/厚10cm，左侧约20cm、右侧较大。低位1.15m终点被拒绝，1.3m低位曲线远期冲突保留；最终通过前向1.25m、z=0.75m的抬高绕行。最新trajectory21完整曲线5601点两张地图均0 inflated，最高z约0.948m；直线实际穿过实物和raw occupied。两个早期远期冲突候选在约3/2ms被替换，实际使用前段+50ms余量及最后全曲线采样均无占据；不声称所有候选全曲线通过。
- 最终run15 epoch 7bfd45ac457e48278c420285ed8b0b72 / map 7bfd45ac457e48278c420285ed8b0b72-770ad2e5b95346d8aaf5b1ded56a1ab2；run16 epoch 67805d52bd0c4a82bec0b7e00ca1d310 / map 67805d52bd0c4a82bec0b7e00ca1d310-ce436bd7c2fb4809977b146c3ad21375。同地图PID226360跨epoch，旧目标ABORT、新图回读、epoch_mismatch与0自动goal。
- 已修复：锁定EGO 0062/0064补丁链，0066完整时间缩放（不恢复在线全曲线硬门），硬件DDS身份缓存/独占对象转发与Foxy action释放、fresh install校验。原生速度参数0.15、实测侧向峰值0.183–0.194，最终绕行峰值0.0905m/s；不是严格0.15限速资格。14个锁定源码/7个实际import匹配，5包ARM构建及受影响重建、8/4/13/10/6项定向、完整ROS接口、实际安装库3例、归档/结构/diff检查通过。
- 约6s最终窗口pending≤2、增加有界丢弃1帧，无持续增长；266条command回调约100Hz、最大间隔22.8ms/接收源龄15.2ms。全部早期源龄锁定、超时、冲突保留。长期/完整负载时效未通过，留HW09；PROVISIONAL rig、含桨包络/控制/时钟映射留HW08。历史SITL资格不覆盖0066，未飞行。
- 收尾：全部所属进程/节点为空；rmem已从8388608恢复保存的212992。部分只读Python组件需SIGTERM，详见报告。不复用旧session；恢复sensor→plan→观察器→localization，实际安装/source预检保留。

- 前置证据：[HW01 ARM](../evidence/hw01-arm-foxy-20261102.md)、[HW02传感器](../evidence/hw02-d435i-20261102.md)、[HW03真实rig](../evidence/hw03-real-rig-20261102.md)、[HW04静态](../evidence/hw04-vins-static-and-stop-20261102.md)/[路线](../evidence/hw04-vins-dynamic-route-20261103.md)、[HW05地图](../evidence/hw05-depth-map-20261103.md)。HW05当时遗留的canonical补丁重放/部署不一致已在HW06闭合；旧证据范围保持，不能外推飞行。

## 历史仿真与快照状态

更新时间：2026-10-30。历史 `sim-nav-v1.0.0` 是已通过 N17 的 X500 版本。当前源码切换到约 250 级仿真近似机体，不能继承旧版的多场景、重复或长时资格，也不代表真实机体标定。

- 当前近似模型与官方地图参数的一次默认房间 16m 任务通过，见[模型适配报告](../evidence/quad250-adaptation-20261030-592.md)；NavRL 多柱场景的 16m GUI/SITL 任务也通过，见[柱群报告](../evidence/navrl-pillars-20261030-600.md)。两者均为单次日常任务，不计入新的正式 N11–N17 次数。
- 当前可复现配置含 `room`（默认）、`floorplan2` 和 `pillars` 场景；多柱演示命令为 `./start.sh fly pillars`。RViz 使用 Orbit 三维碰撞地图视角，保留已探索障碍历史层；#603 相机第一视角试验已撤回。
- 固定容器已单独保存在 `runtime-environment-v1` Git LFS 分支，SHA 和不可变 commit 见 [`docker/environment.json`](../../docker/environment.json)。Linux amd64、NVIDIA/Docker/X11 设备要求及不支持范围见 [README](../../README.md)。
- 当前工作项：将本工作树已有模型、场景、启动、测试和证据修改整理为可复现的 GitHub 快照；目标标签 `sim-nav-quad250-2026-10-30`。干净独立检出已完成全部依赖恢复、18包ROS构建、PX4完整构建、751单测和3套ROS集成；快照发布入口见README。

用户明确要求将现有工作树整体固化并上传。忽略的 `artifacts/` 运行日志/大文件、`.runtime/` 会话状态和机器本地凭据不作为源码发布；历史报告保留相对引用与哈希。

- 2026-10-31 本机RTX3060 Laptop固定标签88a9d08柱群16m GUI单次复现PASS，独立到达/接触/落地上锁/身份及唯一控制全部通过；仅日常单次资格。见[evidence/2026-10-31-local-quad250-reproduction.md](../evidence/2026-10-31-local-quad250-reproduction.md)。GUI已落地上锁，按用户要求保留查看。

- 2026-10-31 RViz默认主视角改为后上方第三人称跟随（位置+yaw，距离6m）。18包构建、5项相关回归及GUI实时TF回读通过，未重飞；当前未解锁GUI保留。见[记录](../changes/2026-10-31-rviz-third-person-follow.md)。

- 2026-10-31 柱群起点依用户累计左移5m至(-14,-9)，终点(9,9)，位移(23,18)，地图X扩到60m。GUI单次原生任务成功并落地上锁，独立到达驻留2.908/3sim秒不足，qualification FAIL；其它检查通过。见[记录](../changes/2026-10-31-pillars-corner-route.md)。当前已落地GUI保留。

- 2026-10-31 同航线新会话gui-20261031-014754-86595重复完成，运行指纹与前次一致；原生成功/无违规接触/落地上锁，独立联合驻留2.204/3sim秒，qualification FAIL。见[记录](../changes/2026-10-31-pillars-corner-repeat.md)。当前已落地GUI保留。

- 2026-10-31 用户要求保存当前代码并冻结RViz第三人称视角：ThirdPersonFollower/6m/Pitch0.6/Yawπ/零焦点偏移；本地标签sim-nav-quad250-follow-2026-10-31，未推送。后续默认保持此视角。见[记录](../changes/2026-10-31-freeze-follow-view.md)。
