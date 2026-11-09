# GS02.3首次动态证据与分段时序采样

首次Debian动态run `hw10-groundstation-20261106T071542Z` 在用户确认回点后正常停止，轨迹/Nano日志见`artifacts/runs/`和[证据](../evidence/gs02-dynamic-circle-20261106.md)。估计端点差8.05cm，路径最大/P95接收间隔1.599/0.437s；Nano有效TRACKING观察142条。未复现032的16.166s路径空窗，但没有动态视觉通道时间线，不能判定其显示停顿原因。

根据该缺口，`tools/diagnostics/hardware_live_rviz.py`现在可选地写5Hz状态JSONL和逐条视觉relay接收事件；样本记录Nano/PC时钟偏移与不确定度、VINS源龄/输入流摘要、视觉源/relay发送/PC接收/PC处理时间、计数及解码状态。事件只记录时间与kind/epoch，不写视觉payload。`tools/groundstation.sh experiment-start`把两类时序文件放进本run目录根部，原轨迹记录及启动默认值不变。

本地验证：`bash -n tools/groundstation.sh`、Python `py_compile`、`python3 tools/test_groundstation.py` 4/4通过。加入了`write_live_status`的append-only样本写入自检于`tools/test_hardware_live_view.py`；本机未安装固定ROS Jazzy镜像，尚未运行该ROS依赖测试，也尚未部署Debian overlay。目标机部署后须运行此测试、`project_status.py`、`uav-groundstation check/status`，再做一轮带采样的用户动态绕圈。

未改PX4固件、参数、同步门限；未启动map/planner/EV/控制、未武装/起飞。当前run已停止。GS02.3和父GS02继续保持未通过。

## 后续目标机验证（2026-11-06）

迁移overlay已部署到`/home/work/D435i-groundstation/releases/gs02-20261106-freeze01/project`，目标Debian固定镜像`python3 tools/test_hardware_live_view.py`通过，覆盖RViz显示帧/轴/odom-TF、原生姿态日志解析和append-only状态样本；目标机`bash -n`、`py_compile`、`python3 tools/test_groundstation.py`（4/4）、`python3 tools/project_status.py`、`uav-groundstation check/status`通过。固定镜像ID未变。

随后用户完成带采样的第二次动态圈`hw10-groundstation-20261106T074153Z`。所有26项run清单通过，文件已取回本地；Debian receive事件出现7.2–10.1s通道空档和最高20.627s send-to-reader延迟，Nano VINS/relay源端没有对应停顿。详细指标见[分段证据](../evidence/gs02-display-pipeline-20261106.md)。此证据将停顿定位到Nano发送后的Debian读取边界，但运行期资源/网络细节和RViz实际paint仍未取证；GS02.3仍未通过。
