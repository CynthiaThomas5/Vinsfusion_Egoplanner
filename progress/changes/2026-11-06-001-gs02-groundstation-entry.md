# GS02 Debian地面站VINS实验入口与部署

实现：增加`experiment-start/experiment-stop`，由Debian启动GPU RViz、只读双目/几何relay及绕圈记录器；两路relay先就绪，再启动Nano `perception --visuals --run-id`。仅允许停止perception层，调用Nano项目正常stop后关闭本次viewer。新增桌面入口、`GROUNDSTATION_CONTEXT.md`接续说明与部署手册。实验入口容器显式加载ROS、venv和接口环境；保留失败容器日志，输出启动失败原因并清理退出容器。安装器保持稳定`project`符号链接路径，便于回退。

部署：Debian旧项目目录及tar备份均保留；`/home/work/D435i-groundstation/project`指向`releases/gs02-20261106-freeze01/project`。桌面入口“启动VINS绕圈实验”已安装。目标机SHA256SUMS 380项、zstd包和结构检查通过；`uav-groundstation check/status`通过，Docker镜像SHA、X11、renderD128和Nano SSH身份保持原值。

启动迭代：第一次GUI启动日志显示漏载ROS/venv导致`pymavlink`导入失败；补齐环境来源。第二次发现ROS setup与`set -u`冲突，改为`set -eo pipefail`。修复后的启动于2026-11-06从Debian成功：run `hw10-groundstation-20261106T062621Z`，20位姿静止基线就绪。正常停止并完整归档于`artifacts/runs/hw10-groundstation-20261106T062621Z/`，24项`RUN-SHA256SUMS`通过。7515条post-baseline姿态持续1050.86s：各轴空间范围6.34/4.25/7.10mm、端点偏移5.81/3.89/-3.73mm、偏移模7.93mm、累计路程0.568m（静止抖动），路径最大/P95接收间隔0.508/0.263s。用户未移动，不能视作绕圈。

29.81s静止relay状态样本120/120 VINS valid、decode errors为0，所有视觉流计数增长，source/transport age最大0.404/0.171s；`clock_uncertainty_s=1.1ms`。该静止窗口不能排除动态或长时显示停顿，032约16.166s显示空窗仍未解释。

正常停止：`experiment-stop`停止Nano perception并关闭`d435i-gs-view`；Nano统一session与sensor session均无owner，进程扫描无D435i/VINS/localization/relay进程，`rmem_max=212992`恢复；systemd Micro XRCE-DDS Agent仍active、保持CH340/TELEM1。Nano现在可关机（PX4 DDS会随Agent离线）；后续动态圈须重上电并从Debian重新启动。静止运行原始目录与24项`RUN-SHA256SUMS`作为迁移覆盖包内容同步到Debian项目相同路径，方便后续会话独立审阅本轮证据。

验证：本地和Debian `bash -n tools/groundstation.sh`、`python3 tools/test_groundstation.py` 4/4、`git diff --check`通过；Debian `python3 tools/project_status.py` PASS、`uav-groundstation check/status` PASS、真实RViz启动、ROS话题记录器与正常停止PASS。**GS02.3未通过**：无用户移动/回起点确认，只有静止段及短时relay连续性数据，不能结案或排除运动时显示停顿。等待用户可移动设备时重新启动纯VINS实验。
