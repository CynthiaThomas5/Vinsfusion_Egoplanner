# GS02.3接收延迟复核与资源/console采样

关联：[用户任务摘要](../../collaboration/dialogues/2026-11-07-001-gs02-reader-resource-instrumentation.md)、[第二次动态链路证据](../evidence/gs02-display-pipeline-20261106.md)。

## 动态证据结论

第二次绕圈run `hw10-groundstation-20261106T074153Z`显示Nano相机/VINS输入及relay发送保持连续，Debian reader的视觉事件和VINS日志在同一时段落后。最大视觉send-to-reader延迟20.627s，视觉计数平台最长29.06s，轨迹接收最大空窗8.302s；PC收到后的排队P95约50ms。问题边界定位到Nano发送后、Debian用户态读取前，但还无法区分网络/TCP/SSH流控与Debian线程/资源调度。run报告不称实际RViz paint已测。

## 实施

- `tools/diagnostics/hardware_live_rviz.py`：每条已有5Hz状态样本附带best-effort host load/可用内存、viewer进程RSS、cgroup CPU/memory/oom、默认网卡字节/错误计数，以及内核提供时的GPU busy计数。无对应procfs/cgroup/sysfs文件时省略字段，不阻断定位显示。
- `tools/groundstation.sh`：正常`experiment-stop`先停止拥有的perception和viewer，再把该Docker viewer的stdout/stderr写入run目录`groundstation/viewer-console.log`，之后移除容器。使用实际Nano session run_id关联日志。
- `tools/test_hardware_live_view.py`增加资源快照自检；`tools/test_groundstation.py`增加stop时日志先保存再删容器的边界测试。
- 原freeze01工作树与基础payload未变；改动以`migration-overlay.tar.zst`独立层部署。

## 验证

- 本机：`bash -n tools/groundstation.sh`通过；`python3 -m py_compile tools/diagnostics/hardware_live_rviz.py tools/test_groundstation.py tools/test_hardware_live_view.py`通过；`python3 tools/test_groundstation.py` 5/5通过。
- Debian目标机：固定镜像`sha256:119e6564...5880a`内`python3 tools/test_hardware_live_view.py`全部显示帧/坐标/TF/原生姿态/状态时间序列/资源快照检查通过；Debian `python3 tools/test_groundstation.py` 5/5通过；`python3 tools/project_status.py` PASS；`uav-groundstation check/status`通过，status为`No unified hardware session`。
- 目标机非登录SSH下的桌面命令别名不在PATH；本次验收以`/home/work/.local/bin/uav-groundstation`绝对路径完成，不影响桌面/登录终端入口。
- 修改文件、上下文和第二圈完整run数据已进入`artifacts/releases/gs02-20261106-freeze01/migration-overlay.tar.zst`，其身份记录在release `manifest.json`。Debian release目录内`sha256sum -c SHA256SUMS` 380项通过，overlay zstd检查通过；解包后第二圈26项`RUN-SHA256SUMS`通过。Debian部署项目重新执行`project_status.py`、地面站边界测试、固定镜像测试、`uav-groundstation check/status`均通过。

## 边界与下一步

此次只验证采样实现，不是动态资源数据，不构成显示问题修复。第二圈证明高时延窗口后积压会排空，不能证明后续长时间不再复发。未改Nano算法、PX4固件/参数/同步门限；未启map/planner/EV/control、未武装/起飞。迁移overlay同步完成；用户回来后按资源/网络指标决定是否再做一次短慢速动态回归。GS02.3保持未通过。
