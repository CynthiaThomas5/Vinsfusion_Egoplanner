# 修改与验证记录

- 任务 ID／日期：SYSTEM-AUDIT-001-PLAN / 2026-11-08。
- 对话摘要：[规划摘要](../../collaboration/dialogues/2026-11-08-002-system-remediation-plan.md)。
- 改动：新增[四批实施计划](../../docs/tasks/SYSTEM-AUDIT-001-remediation-plan.md)，向 CURRENT 添加计划入口，审查报告补充方案复核说明；随后按用户授权实施四批修复，并在本记录续记代码改动与验证结果。
- 原因：复核地图 revision、MapStatus/查询契约、rig 双序列号、构建环境与子 shell 调用，避免把身份变化当融合进度、把两种 serial 混用，或切换安装时混用新旧产物。
- 验证类型：定向回归、结构检查、语法和差异检查。详见下方；目标机构建和硬件链路不在当前工作站执行。
- 未验证：Nano ARM/Foxy fresh build、sensor/perception/map 地面链路；导航 ROS 集成测试已尝试但因缺 `rclpy` 在导入阶段退出，深度率 ROS 测试因缺 `ament_index_python` 在导入阶段退出。本机 x86_64 且无 ROS Foxy。SSH 到 `uav-nano` 的只读连接被本地网络沙箱以 `Operation not permitted` 拒绝。硬件主线 HW10-EV-028 及资格保持原状态。
- 下一步：将当前修复部署到 Nano，先核对安装清单和 SDK 身份，再验证 sensors/perception/map 最小地面链路；不因此启动 EV/control 或飞行。

## 原计划阶段检查结果（实施前记录）

- `python3 tools/project_status.py`：Structure/design check PASS；347 个可选历史产物链接缺失，未将其记为补齐或运行通过。
- `git diff --check -- progress/CURRENT.md docs/reviews/system-audit-20261108.md`：无空白错误；新增文档另行检查尾随空白与本地 Markdown 目标路径，PASS。
- 当前 HEAD `dbb724f`，生产修复未实施。本轮仅文档规划完成；不据此登记代码/目标机通过。
- 文档 SHA256 `docs/tasks/SYSTEM-AUDIT-001-remediation-plan.md`：`6342a8b7e7567ce983180e88e12e8258a425f90f91e96fde7dbdff2853e91040`。
- 文档 SHA256 `docs/reviews/system-audit-20261108.md`：`e32f88e5091a74c8615e2e2927e9a570200484b7623720a7ed478d37ced17539`。

## 四批实施与本地验证

- 修复落地：启动状态独占预留与统一收尾；build 与 start 共用会话预留，独立 sensors 入口进入统一生命周期；旁路状态按 run 目录核对所有权；停止分支不加载启动专属环境；运行状态保存配置、频率、rig 哈希且子进程核对一致性；层级 profile 和 D435i 双序列号同记录匹配；fresh build、安装清单和固定安装路径；导航 stale 查询退避并在等待后复核地图上下文；删除无效深度计数函数/测试。RealSense SDK 软件身份集中到部署 profile，不再重复写入 rig。
- 定向回归：`test_hardware_session.py` 14/14、`test_hardware_profile.py` 6/6、`test_hardware_build.py` 4/4、`test_mapping_input.py` 5/5、`test_navigation_task_state.py` 10/10、`test_hardware_rig.py` 4/4，共 43 个用例；`test_navigation_terminal.py` 也通过。build suite 以假 colcon 测构建失败/安装核验失败不激活旧入口、成功后的原子激活，以及安装后源码变化会被清单拒绝；它不替代 Nano 实际编译。
- 静态/结构：相关 Python `py_compile`、硬件 shell `bash -n`、`git diff --check` 通过；`project_status.py` Structure/design check PASS。报告中的 347 个缺失项属于可选历史产物链接，不计作生产故障或测试通过。
- 环境限制：`test_depth_output_rate.py` 因缺少 `ament_index_python`、`test_navigation_adapter.py` 因缺少 `rclpy` 在导入阶段退出；Nano 构建/实机链路尚未运行。本机结果不代表 ROS 构建或硬件资格。直接查询 Nano 时，本机网络沙箱拒绝了 SSH socket，无法完成目标机验证。
- 回退边界：工作树含大量本任务之外的既有改动，共用导航文件也包含其它任务修改；未将四批拆成独立 Git 提交，当前不能声称提交级可单独回退。未暂存或提交混合工作树。
