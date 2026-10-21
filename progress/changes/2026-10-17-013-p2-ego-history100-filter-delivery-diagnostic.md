# P2 EGO pose history=100 filter 交付诊断

日期：2026-10-17。对话摘要：[2026-10-17-013-p2-ego-history100-filter-delivery-diagnostic.md](../../collaboration/dialogues/2026-10-17-013-p2-ego-history100-filter-delivery-diagnostic.md)。

- 修改：新增可选补丁 0016，在 patch 0015 诊断分支上仅将 EGO `PoseStamped` reader history 从25改为100；补丁基于 post-0015，不与 0014 分支组合。隔离副本 patch replay byte compare 通过，Jazzy build #08 的5个 EGO 包构建通过；`src/vendor` 未修改。
- 运行：#38因辅助 launch 文件指向不存在的 world 路径，未启动 VINS/EGO，排除。#39虽有 READY 深度，但定位在5.908 wall秒后锁定 `telemetry_stale` 并触发清图，60.023秒 probe 仅有18组输出，排除。#40使用与#37相同的启动辅助文件、domain、partition 和 world 路径，只更换输出目录及 EGO install overlay。
- #40有效健康窗口60.034秒：深度 READY、定位 TRACKING、raw VINS 242优化/3182传播输出，EGO得到554组配对，地图峰值1916点。paired source interval p50/P95/max为0.033/0.165/0.495秒；EGO pose wall receipt interval为0.106844/0.248998/0.866541秒。窗口内29条 timeout，另有4条在窗口后。首个诊断组中 pose receipt停在73，depth receipt由79增至92，pose stamp停在9.076秒，两个 message-lost 计数均为0。history=100没有消除该间断。
- 解释：本轮单次有效运行足以否定“history=100稳定消除停顿”，但不足以统计比较停顿频率或认定根因。Fast DDS把 writer 声明样本丢失与 reader 因资源上限拒收样本作为不同状态；当前 RMW 观测到的零 `message_lost` 不能排除拒收或 executor 延迟。#39 ROS graph 对 history depth 报 `UNKNOWN`，故没有运行时 CLI 深度读回证据；实际配置由隔离构建源码确认。
- 验证：patch replay byte comparison 通过；build #08 五包构建 exit 0；run #40 probe exit 0；三份运行脚本 `bash -n` 通过；证据 JSON 与选定 artifact SHA256 校验通过；`python3 tools/project_status.py`、三份复测脚本 `bash -n`、`git diff --check` 与 `git diff --cached --check` 均通过；容器运行进程审计无活动仿真／VINS／EGO／mapping 进程。
- 局限与下一步：patch 0016仅为诊断，不改生产依赖链。0.4秒 timeout 与 `ground_height=-0.15 m` 仍为 PROVISIONAL。先采集 reader resource rejection 或 executor dispatch 证据；涉及多线程前须解决 GridMap 输入、timer、reset 共享状态无互斥的问题。无 goal、controller、PX4、actuator、故障响应或正式验收。
