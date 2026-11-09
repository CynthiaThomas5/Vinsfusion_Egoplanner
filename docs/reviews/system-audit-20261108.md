# 2026-11-08 系统静态审查报告

2026-11-08 方案复核：具体实施以[四批修复计划](../tasks/SYSTEM-AUDIT-001-remediation-plan.md)为准。导航 `_map_revision` 只代表身份变更，不能用于等待新融合；API/ASIC serial 须分别核对各自配置字段。构建先隔离产物并统一安装入口，暂缓哈希缓存系统。以下代码行号为初次审查时位置。

## 结论

本轮确认 **2 项高优先级运行流程问题、4 项中优先级数据/构建问题、2 项低优先级遗留复杂度**。主要风险来自“状态/配置由多个地方表达”，不是一个孤立算法错误：CURRENT 同时保留互相冲突的运行状态；统一启动器在检查完成前写入会话状态；硬件深度频率和相机身份也分别由配置与脚本重复决定。

建议按“先保证操作员看到唯一现状 → 启动失败不留下假会话 → 构建与配置只有一个可信来源 → 删除死代码”的顺序修复。当前真实设备资格边界仍是 HW08/HW10 未完成，下一条主线为 HW10-EV-028；本报告没有扩大其资格或授权范围。

## 审查范围与限制

- 检查项目入口与目标、CURRENT/里程碑、架构与接口契约、硬件手册和配置；静态追踪统一硬件启动、传感器与定位、映射、导航准入、PX4 桥以及相关状态/构建检查。
- 本轮开始时工作树已有 353 项修改或未跟踪项。未回滚、整理或覆盖这些现有内容；只新增本报告和配套审查记录。
- 这是代码与文档静态审查。没有运行单元测试、构建、仿真、SITL 或真实硬件，也没有逐行审计第三方上游源码。因此，报告能确认代码结构和逻辑风险，不能替代目标机复现、运行图检查或飞行资格证据。

## 已确认问题

### A1 · 高：当前状态文件里同时宣称“会话已停止”和“旧会话仍在运行”

[progress/CURRENT.md](../../progress/CURRENT.md#L5) 至 [progress/CURRENT.md](../../progress/CURRENT.md#L22) 记录 11 月 7 日收尾：Nano unified session 为空、VINS/localization/relay 进程不存在，下一项是 HW10-EV-028。该文件后面 [progress/CURRENT.md](../../progress/CURRENT.md#L33) 至 [progress/CURRENT.md](../../progress/CURRENT.md#L39) 又以“用户当前查看”标题声称 HW10-VIEW-030 仍在运行，并指示正式试验前先停止那组旧 PID。

**根因链：** CURRENT 被同时用作当前状态、最近工作总结和历史交接日志；新状态写在顶部，旧“当前”小节未退休。操作员若从下方恢复上下文，可能重复停止、误认为 Nano 有残留 VINS 会话，或错过实际下一项。

**简化方案：** CURRENT 仅保留一个现行状态块和唯一下一项；HW10-VIEW-030 的运行细节已在对应 evidence/change 中有存档，应从 CURRENT 删除或移入明确标记的历史交接页。`docs/hardware-running.md` 还有标成“当前”的 11 月 4 日地面融合章节，应在标题标注为历史操作记录并指回 CURRENT，不再承担实时状态源。

### A2 · 高：统一启动器的会话记录先于环境检查落盘，部分参数在启动硬件后才拒绝

[tools/hardware-session.py](../../tools/hardware-session.py#L118) 至 [tools/hardware-session.py](../../tools/hardware-session.py#L129) 先创建运行目录和 `.runtime/hardware-session.json`，然后才执行安装检查。安装检查发生在 `try` 清理范围之外。任何安装/导入检查失败，都会遗留一个看似占用中的会话；后续 `start` 会拒绝运行，`stop` 也只能处理这份空进程记录。EV/control 层的 `stop()` 按设计拒绝自动拆链，所以同一失败尤其难以由常规 stop 清理。

此外，[`--measure-seconds` 的组合与正值检查](../../tools/hardware-session.py#L150) 位于传感器、映射/规划和桥接器启动之后；无效值会先启动硬件再抛错。`--visuals` 配合 `sensors` 会在传感器启动后提前返回，选项被静默忽略。

**根因链：** 持久会话文件既被当作互斥锁，也被当作已拥有资源的运行状态；命令参数、环境预检、资源启动没有清晰阶段边界。

**简化方案：** 将参数、层级组合、rig 准入和安装检查全部放到创建运行目录/会话状态之前；预检完成后再建立会话。持久状态只记录成功启动并确认身份的资源，启动中断按已登记资源回滚。保留 EV/control 的安全停止要求，不能因为重构而让启动器自动终止未知控制链。

### A3 · 中：硬件增量构建仍依赖默认 colcon 缓存，安装内容核对没有覆盖传感器 C++ 输出

[tools/hardware.sh](../../tools/hardware.sh#L228) 至 [tools/hardware.sh](../../tools/hardware.sh#L239) 执行默认 `colcon build`，没有隔离的 build/install 前缀。Nano 与开发机时钟不同；[docs/hardware-running.md](../../docs/hardware-running.md#L23) 已要求传文件后按内容而不是 mtime 判断。历史记录也确认曾备份旧 build/install 缓存并以 fresh build directory 解决陈旧产物问题（[2026-11-03-002 记录](../../progress/changes/2026-11-03-002-hw05-map-only-launch.md#L43)）。

当前防线不完整：[tools/check_hardware_install.py](../../tools/check_hardware_install.py#L1) 只逐字节比较 localization 与 PX4 bridge 的 Python 文件；规划 launch 另查 navigation Python 与 EGO 补丁哈希，但传感器驱动适配器的 `depth_to_meters.cpp` 安装产物没有同等核对。于是 colcon 的时间戳判断仍是隐式构建输入，传感器 C++ 陈旧时存在漏检路径。

**根因链：** 构建可复现性依赖机器时间/历史缓存；源码一致性检查只覆盖部分运行文件。

**简化方案：** 硬件构建使用隔离的 fresh build 前缀，成功后再切换运行安装；或以源码/依赖身份选择内容化 build/install 前缀。把实际运行的传感器 C++ 产物纳入源/构建身份检查。保留旧前缀供回退，不清空无关缓存，也不通过改文件时间戳或修改设备时钟来绕过。

### A4 · 中：深度输出频率配置存在两个权威值，统一启动器又覆盖两者

[config/hardware/mapping.json](../../config/hardware/mapping.json#L88) 声明 5 Hz，[config/hardware/planner.json](../../config/hardware/planner.json#L14) 声明 3 Hz；但 [tools/hardware-session.py](../../tools/hardware-session.py#L129) 对所有层都固定设置 `HW_DEPTH_OUTPUT_HZ=3.0`，再由 [tools/hardware.sh](../../tools/hardware.sh#L137) 传给传感器 launch。map-only 因而不使用其 mapping profile 中声明的 5 Hz。当前不同入口/层级拿到的运行频率不是由一个确定的 profile 决定。

**根因链：** 配置文件声明了期望值，shell 环境覆盖却成为真正运行值；启动器没有按层解析配置。

**简化方案：** 删除统一启动器中的常量，按层从现有 profile 解析唯一值：map 使用 mapping profile，plan/EV/control/full-load 使用 planner profile；sensor/perception 的策略显式定义在已有配置中。启动状态保留已解析配置路径和哈希，便于还原实际输入。

### A5 · 中：物理相机序列号在 rig、shell 和 ROS launch 中重复维护

序列号 `243622073269` 同时出现在 [config/hardware/rig.json](../../config/hardware/rig.json#L5)、[tools/hardware.sh](../../tools/hardware.sh#L38) 和 [d435i.launch.py](../../src/own/uav_sensor_interface/launch/d435i.launch.py#L18)。shell 检查与启动会话使用自己的字面值；rig 则决定映射/定位使用哪组相机标定。当前数值一致，但换相机或更新其中一个文件时，采集设备与所用标定可能分离。

SDK 身份已有 `realsense_sdk.json`，但 shell 仍包含默认 wrapper 前缀/路径和局部版本检查值，尚未收敛到一个硬件身份描述。

**根因链：** “实际采集设备身份”与“几何标定身份”由不同文件分别决定，没有启动前等值约束。

**简化方案：** rig 作为 serial 的唯一来源，由启动器把 API serial 作为 launch 参数传下去；枚举设备时将 API serial 与 rig.identity.api_serial、ASIC serial 与 rig.identity.asic_usb_serial 分别比较，不一致就拒绝继续。逐步把 wrapper/SDK 路径与身份核对并入现有版本化硬件 profile，删去 shell 中重复字面值。

### A6 · 中：导航对地图过期拒绝会以 5 ms 间隔重复发起相同查询

[导航 `_query_target`](../../src/own/uav_navigation/uav_navigation/node.py#L321) 固定了同一 request、map_id 和读取时的 revision。地图因 `no_fresh_fused_depth`、`occupancy_update_stale` 或 `depth_source_stale` 拒绝时，代码只 `sleep(0.005)` 后重新调用服务（[第 341–345 行](../../src/own/uav_navigation/uav_navigation/node.py#L341)），没有等待 map revision/fusion stamp 改变。快速响应时单个请求最多接近每秒 200 次相同查询，直到原 timeout 到期；在地图正因数据不新鲜而忙碌时，这会增加服务负担，却不增加信息。

**简化方案：** 在同一截止时间与取消检查内采用有上限的退避，避免反复请求；地图身份变化时拒绝原请求。现有 `_map_revision` 不表示融合进度，不据此等待或新增通知话题。不要重置原始 deadline，也不要因新鲜度等待而放宽碰撞/地图准入。

### A7 · 低：深度有效像素统计函数已脱离运行路径，只有测试仍保留它

[valid_depth_sample_count](../../src/own/uav_mapping/uav_mapping/mapping_input.py#L100) 在生产代码中没有调用点；唯一引用是 [tools/test_mapping_input.py](../../tools/test_mapping_input.py#L12) 及其相关用例。运行入口检查的是消息布局，README 也明确没有最小有效像素数门。

**简化方案：** 删除该 helper、无效的 `struct` import 及专门测试；保留仍在运行路径使用的 `depth_layout_valid` 和 CameraInfo 检查。此项不改变现行地图准入行为。

### A8 · 低：统一会话默认 run ID 仍使用 `hw09-` 历史前缀

[tools/hardware-session.py](../../tools/hardware-session.py#L115) 为 sensors、map、plan 等所有层默认生成 `hw09-<UTC时间>`，而当前运行与主线记录已进入 HW10/groundstation 阶段。目录尚可唯一标识单次运行，但默认命名会把新数据归入旧代号，降低搜索、归档和故障关联的可靠性。

**简化方案：** 改用无历史阶段含义的 `hardware-<layer>-<UTC时间>`；若 observer 脚本名也只含 `hw09`，统一中性命名并保留旧文件名兼容入口（如果有外部调用）。

## 系统不变量与复杂度审视

- 主架构边界清楚：单地图 owner、mapping adapter 负责真实深度/位姿输入契约、navigation 负责 action 与地图准入、PX4 bridge 是控制输出边界。静态审查没有发现生产链路中第二个 PX4 控制发布者；这不是运行时 ROS graph 验证。
- Epoch、map_id、目标 ID、源戳/接收龄分离及单调时钟超时属于必要不变量。用户已将实机飞行排除在当前通过范围之外；不能把文档/脚本中的“硬件启动”误读成飞行准入。
- `compute_plan`、full-load 的 `compute_only`、rig MEASURED/control_usable 检查和 EV/control 的停止保护都改变了有效安全/功能边界，不是无效开关；本轮没有建议删除。
- N08/N10 多组参数 profile 多数带有实验身份或证据引用。没有按文件名批量判废；应先建 active/archive 索引，只归档经引用检索确认无人复用的候选。
- A7 是已证实的可删除死代码；A4/A5 是合并配置来源；A2/A3 是减少启动/构建隐式状态。没有理由为这些问题再叠加并行的状态文件、另一套配置系统或多层重试保护。

## 建议修复顺序

1. 先修 CURRENT/历史章节标识，避免操作员从过期“当前”状态执行硬件命令。
2. 重排启动器：全部输入验证与预检在资源分配前完成，再创建 run/session；补清楚启动中阶段与已拥有进程的边界，保留 EV/control 停止安全约束。
3. 统一深度率和物理设备身份的配置来源；硬件 start 记录解析后的配置身份并拒绝设备/rig 不匹配。
4. 让硬件构建不再靠默认历史缓存判定新旧，并完整覆盖实际运行 C++/Python 产物。
5. 改地图服务等待为 revision 驱动/有界退避，删除失效深度计数 helper 和过时 run 前缀。

## 本轮结果

没有改动生产代码、参数、设备状态或当前任务资格；本报告及对话/变更摘要是本轮唯一新增内容。没有运行测试、构建、SITL 或实机流程。上述修复尚未实施；下一步可从优先级 1–3 开始逐项修改并按目标机验证。
