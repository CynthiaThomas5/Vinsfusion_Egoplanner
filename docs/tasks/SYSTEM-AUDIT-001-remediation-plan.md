# SYSTEM-AUDIT-001 修复实施计划

日期：2026-11-08。状态：四批实现已落地；可运行的本地定向检查通过，ROS 依赖用例及 Nano ARM/Foxy 构建与硬件链路待目标环境确认。
依据：[静态审查报告](../reviews/system-audit-20261108.md)。本任务是维护修复，不推进 HW10-EV-028，不产生硬件通过资格。

## 实施原则与方案修正

每批只解决一类根因，独立审阅和回退；先完成本地实现与回归，再安排目标机部署验证。现有工作树有大量未提交内容，实施前保存所改文件的当前副本/差异，以本轮改动前内容作为回退基线，不能直接恢复 HEAD 覆盖已有修改。

以下三处收敛前一版建议，实施时以本计划为准：

- `_map_revision` 在 navigation 的 `_on_map()` 中只随 epoch/map_id 变更递增，属于身份代数；不能改成每次消息都递增，也不能等待它代表新融合。MapStatus 的 last_depth_source_stamp 是转发输入时间，last_occupancy_stamp 是占据云消息时间，也不能直接当作实际融合完成时间。
- rig 中 API serial 为 243622073269，ASIC/USB serial 为 243323065857。两者分别与 `identity.api_serial`、`identity.asic_usb_serial` 核对，不能相互比较要求相同。
- 构建先用全新 build/install 目录和统一安装入口解决旧产物混用；暂不实现源码哈希缓存、自动垃圾回收、构建守护进程。A3 是已存在过故障的防线缺口，本轮没有证明当前设备的 C++ 产物已经陈旧；A8 是可维护性问题，不按严重运行故障处理。

## 批次 1：当前状态与启动生命周期（A1、A2、A8）

### 修改范围

`progress/CURRENT.md`、`docs/hardware-running.md`、`tools/hardware-session.py`、`tools/test_hardware_session.py`。

### 实施步骤

1. CURRENT 保留最新确认的收尾、资格边界和唯一下一项，历史交接移到历史页/既有 evidence 与 changes 索引；从现行摘要移除“VIEW-030 仍在运行”等过期表述。只依据已有证据整理文档，实际设备状态仍由 status/现场回读确认。
2. 在任何 run 目录、会话状态和进程创建前验证 CLI：measure 仅 full-load 接受，数值须有限且大于零；sensors 与 visuals 组合明确拒绝；run ID/架构/rig/安装环境全部预检。对传感器需要打开设备的就绪检查仍放在真正启动阶段。
3. 预检通过后，用同一会话状态文件的排他创建保留会话，避免两个 start 同时通过存在性检查；构建激活也短暂占用该文件，不增加第二份锁。独立 sensors 入口转入统一会话所有权。状态记录操作/阶段，资源列表记录 PID 与 start ticks。旧状态文件读取保持兼容。
4. 所有取得资源后的异常进入同一收尾路径：只清理本次登记且身份匹配的资源；sensor/localization 旁路状态的 run 目录必须与当前 run 相同才允许 stop；清理完成才能解除会话占用；清理失败保留状态并说明原因。运行目录保留日志作为失败证据。
5. EV/control 在 bridge 尚未尝试启动前可清理已拥有的地面组件；一旦尝试启动可能向 PX4 输出的 bridge，就按当前保守停止规则保留监护。仅凭一个布尔位、空 PID 列表或未收到 ready，均不能证明输出不存在。手动 stop 的安全限制保持。
6. 默认 run ID 改为 `hardware-<layer>-<UTC时间>`，显式传入的旧 run ID 继续有效。旧 recorder 脚本名不为美观而新增兼容包装器。
7. stop 路径不加载相机 SDK profile、ROS overlay 或运行安装；这些只属于 start/status 的依赖，避免启动配置损坏时反过来阻断进程清理。

### 完成标准

- 非法参数/失败预检：没有新进程、没有新 session 状态、没有 run 目录。
- 两个并发 start：最多一个拥有会话；失败者不能删除胜者状态或资源。
- 在传感器、sysctl、配置生成、map/plan、localization 启动点注入失败：安全层正确收尾，rmem 仅按已记录原值恢复；收尾失败时不宣称已停止。
- EV/control 未知输出状态仍拒绝自动拆链；PID 被复用时不得发信号。
- 文档只有一份现行交接状态，历史证据保持可追溯。

## 批次 2：配置与物理身份来源收敛（A4、A5）

### 修改范围

`tools/hardware-session.py`、`tools/hardware.sh`、`src/own/uav_sensor_interface/launch/d435i.launch.py`、既有硬件运行配置、相关测试和使用文档。拆成“深度率”和“设备身份”两个可单独审阅的补丁。

### 实施步骤

1. 层级解析只做一次：map 从 mapping.json 读取 5 Hz；plan/ev/control/full-load 从 planner.json 读取 3 Hz。sensors/perception 保留当前统一入口实际使用的 3 Hz，写入明确的传感器运行配置；独立传感器 launch 的 0 Hz 无上限语义保留。尽量使用已有合适运行配置字段，确无合适归属时只增加一个小传感器运行配置，不建立通用配置注册系统。
2. 删除统一启动器中的固定环境赋值，向子进程传递解析后的值；拒绝负值、NaN、无穷等无效配置。运行记录保存实际层级、频率、配置路径与哈希，不能仅记录一批未实际使用的配置文件哈希。
3. shell 从 rig 读取 API/ASIC 身份；launch 声明必须传入的 serial 参数，shell 按 wrapper 既有格式传递。直接 launch 缺 serial 时明确失败，避免自动选择错误设备。
4. 枚举结果必须能将 API/ASIC 绑定到同一 `Device info` 记录，再分别与 rig 核对。无设备、多匹配、身份错配均在采集前拒绝；保留 device-identity.txt 的实际观察值。
5. SDK/ROS wrapper 的部署路径、版本、提交和哈希归入已有版本化 profile；rig 只保留硬件/标定身份，不重复保存同一份软件版本。环境覆盖若保留，必须校验实际加载身份，不引入静默回退到另一版本。

### 完成标准

- 修改 mapping profile 后，map 的实际传参随之改变；planner 层读取自己的 profile。
- 改 rig 序列号后 shell 与 launch 一致改变，源码不再保留第二个运行 serial 字面值。
- 正确 API/ASIC 配对可通过；API 正确而 ASIC 不符、设备记录错配必须拒绝。
- 深度单位、图像尺寸/坐标系/源戳保持接口契约；只改变已明确指定的输出限频策略。

## 批次 3：硬件构建与安装选择一致（A3）

### 修改范围

`tools/hardware.sh`、`tools/hardware-env.bash`、`tools/hardware-localization.sh`、`tools/check_hardware_install.py` 及所有硬编码 source workspace/install 的子 shell。先列完整调用点，再统一改入口。

### 实施步骤

1. 每次正式硬件构建使用新建的独立 build/install 前缀，失败产物不能成为启动默认安装。原安装前缀保持可回退。
2. 构建成功后保存小型构建清单：参与构建的实际源码内容指纹、依赖身份、工具链信息与安装文件哈希；未提交修改也必须反映在指纹中，不能只用 git commit 判断。
3. 在没有硬件会话运行时才激活新安装；构建短暂排他占用统一会话状态文件，避免 start/build 检查与激活之间发生竞态。会话启动时解析并固定一个绝对安装路径，传给所有子 shell。sensor、VINS/localization、map/plan、bridge 必须使用同一选择结果，不能只有 hardware-env 使用新目录而子 shell 继续 source 旧 install。
4. 安装核对覆盖实际运行的自维护 Python、launch/config/package.xml、self-maintained lib 输出与 sensor C++ 可执行文件；launch/config 与源码逐文件比较，安装文件及 native binaries 由清单哈希核查，不尝试直接将二进制与 C++ 源文件作字节比较。保留既有上游来源锁检查。
5. 缺清单或内容不匹配时给出明确重建/恢复入口；迁移旧安装前先记录身份，不能因为增加检查就无提示切换或破坏现有固定环境。

### 完成标准

- 仅改源码内容、保持旧 mtime，新构建仍产生对应新安装；改 Python、C++、launch/config 均可被核对发现。
- 构建失败不改变当前安装；已有会话期间不切换安装。
- 各层实际解析到同一固定前缀；恢复旧前缀后原入口可重新使用。
- 该批需 Nano ARM/Foxy 实际构建与最小 perception/map 启动核验。本地静态检查通过只能记为待目标机验证。

## 批次 4：导航查询减负与死代码清理（A6、A7）

### 修改范围

`src/own/uav_navigation/uav_navigation/node.py`、`src/own/uav_mapping/uav_mapping/mapping_input.py`、现有 navigation/mapping 测试。

### 实施步骤

1. 只对三类暂时性地图新鲜度拒绝启用有上限退避，例如 20/40/80/100 ms；等待不得越过原 wall deadline，期间保持取消/退出响应。等待结束后、再次查询前重新检查 epoch/map_id/准入状态；身份变化直接拒绝，不向新地图悄悄迁移旧请求。
2. 最终是否接受仍由查询响应的 epoch/map_id、last_fusion_stamp 等既有契约判定；不复用过期 free 结果，不修改 `_map_revision` 身份语义，也不新增“融合通知”话题或常驻观察器。
3. 删除 valid_depth_sample_count、其唯一 struct import 和仅为该死函数服务的测试。保留布局检查、CameraInfo 检查及相关有效用例。

### 完成标准

- 连续 stale 响应下查询次数有明确上界；可恢复时仍能在原 deadline 内完成准入。
- 取消、shutdown、地图身份变更及时结束等待；相同 timeout 不被每轮重置。
- 深度全零数据仍按现行布局/地图规则处理，不恢复已废弃的有效像素数健康门。

## 交付、验证与边界

推荐顺序：批次 1 → 批次 2 → 批次 3 → 批次 4。每批单独记录文件差异、回归结果和未解项；批次 4 的本地实现不依赖目标机，但硬件运行验证必须使用批次 3 已确认的安装身份。

本地验证优先扩展已有 `test_hardware_session.py`、`test_hardware_rig.py`、`test_depth_output_rate.py`、`test_navigation_adapter.py`、`test_mapping_input.py` 中与真实失败路径对应的用例，不建立第二套测试框架。构建步骤用可控失败验证“失败不激活”；导航使用可控服务响应验证次数、超时、取消与身份变化。

目标机验证先做构建/安装身份检查，再做受影响的 sensors/perception/map 地面最小链路。只有更改跨到仿真公共路径时才安排受影响的 SITL 回归。此计划不启动 EV/control、武装或飞行；那些操作按 HW10 自身前置条件与授权单独执行。

每批退出条件是实现与该批可运行检查通过、限制如实记录；测试通过、构建通过、目标机链路通过分别记账。旧参数 profile、历史日志/证据和第三方源码不因名称陈旧批量删除。

## 当前执行状态

当前进度：批次 1–4 的代码/文档修改均已落地。启动器、profile、映射输入、导航状态、rig 和 build activation 定向回归共 43 项通过；build 测试用假 colcon 覆盖成功激活、编译失败不切换、安装文件核对失败不切换，以及安装后源码变化会使保存清单失效。另覆盖并发构建/启动互斥、启动各阶段故障收尾、foreign sidecar 拒停、停止无启动环境依赖、设备同记录匹配和安装 launch/config 一致性。Python 编译、shell 语法、`git diff --check`、导航终态检查和 `project_status.py` 通过。ROS 深度率测试因缺 `ament_index_python`、导航服务集成测试因缺 `rclpy` 均在导入阶段退出。当前工作站是 x86_64 且无 ROS Foxy；访问 Nano 的 SSH 连接被本地网络沙箱拒绝，故 Nano ARM/Foxy fresh build 与 perception/map 地面链路尚未验证。目标机验证不能由本地静态结果替代。

Git 回退边界：当前分支工作树还包含大量本任务之外的未提交/未跟踪改动，且导航节点等共用文件混有不同任务修改；本轮没有创建四个独立 Git 提交，也没有暂存或覆盖这些改动。故目前的“分批”指实现范围和回归范围，尚未证明可按 Git 提交单独回退。需要在干净基线/独立 worktree 中重建批次提交后，才能将该项记为完成。
