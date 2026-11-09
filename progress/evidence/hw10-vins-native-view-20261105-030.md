# HW10-VIEW-030：原生VINS可视化与第二圈观察

用户明确要求修复RViz不能拖动，并恢复以前的VINS-Fusion稀疏点、相机视锥、左右目跟踪图。随后询问是否可移动并完成一圈，要求检查是否漂移。只运行perception及显示，不运行EV/控制/武装/飞行，不改固件/参数/健康门限，不推进028正式动态验收。

## 显示修复与实证

旧配置未显式加载视角Tools，旧RViz约900%CPU且未出现在NVIDIA图形进程中。补config/rviz/hardware_live.rviz：MoveCamera第一默认工具，附Interact/Select/FocusCamera，**不加载SetGoal/InitialPose工具**；固定hardware_display观察、刷新30→15Hz、默认距离12→5m。窗口源文件不硬编码多显示器坐标；本run副本放在主屏。

旧显示窗口无响应，SIGINT/SIGTERM后仍不退出，核验PID仅为已保存数据的RViz后强制关闭；未杀相机/估计/控制进程。新RViz使用NVIDIA PRIME环境（__NV_PRIME_RENDER_OFFLOAD=1、__GLX_VENDOR_LIBRARY_NAME=nvidia），OpenGL4.6，nvidia-smi实际列出rviz2/195MiB，启动后约85%CPU（非受控性能基准）。实际鼠标响应仍以用户操作为准，不把配置检查当物理拖动证据。

使用已有双通道relay，不重写官方算法输出：camera_pose_visual、point_cloud、margin_cloud、image_track和imu_propagate，分别转为隔离hardware_view显示话题。左右目在640×240预览左右各一半，有真实特征标记，已检查stereo-tracking.png。image与geometry分流/latest-slot；Nano perception --visuals等两个relay预热完成才启动VINS，减少增加订阅扰动。

4s实际PC回读image17、points25、history6、camera25；当时点100、历史点1、相机Marker2；每类各有一个RViz订阅，无fmu/in话题。运行status后续持续增长，decode错误空、健康valid。PC域83/localhost，Nano原域只读订阅/SSH显示，不发送PX4输入。

## 用户第二圈观察

epoch6812e30a222546e0ba2ede44bff26508，保存完整1800姿态保留路径（after-hold-path.json）、增量记录与原定位日志。增量记录器接入时用户已在途中，所以circle-start.json不能当圈起点；没有把途中点到终点2.7m误算漂移。采用完整session路径最初静止位置与返回后保持位置，各20姿态中位数：

- 起点(-0.0092,-0.1974,0.0118)m，终点(0.0040,0.1283,0.0474)m。
- 水平首尾差0.3260m、高度差+0.0356m、3D差0.3279m；估计yaw相差约2.61°。
- 已取原定位日志243条：初始化3条等待，首次valid后无失效/锁定，epoch唯一；返回静止后的最后10条观察位置各轴跨度约0.50/0.12/0.39mm，首尾约0.41mm，仅为该段估计稳定性，不是毫米级真实精度。

结论：轨迹持续跟踪，静止后未见持续发散，但存在约0.33m估计闭合差；若物理回到同一点/朝向，可作为累计误差线索，实际手持返回位置/高度/姿态和近似杆臂未被独立量测，不能直接宣布0.33m绝对定位误差。当前perception只跑局部里程计，没有loop_fusion回环校正；没有声称闭环优化或尺度/导航验收通过。后续若用户澄清物理返回不同，保持观察值但相应撤回误差解释。

## 命令、验证与保留运行

- Nano `bash tools/hardware.sh start perception --visuals --run-id hw10-vins-official-view-20261105-030`：新session/两relay预热/固定VINS运行通过，Nano状态见nano-active.json。
- PC Humble域83 `hardware_live_rviz.py --live --vins-only --visuals --run-path <030run>`及NVIDIA环境下`rviz2 -d <030>/official-view.rviz`：真实显示窗口、订阅/数据/原生消息检查通过。
- `python3 tools/test_vins_visual_transport.py`、`python3 tools/test_hardware_live_view.py`：标准消息/JPEG/Foxy Marker兼容/epoch/frame/错误输入、显示轴/杆臂/日志解析通过。Tools配置断言MoveCamera默认、无控制工具通过。未重建算法/ROS包、未跑SITL或飞行。
- 圈增量记录器已停止；030全套实时view、RViz及Nano perception/两relay按用户查看需求保留，当前不是029快照。不得把camera关闭或时间过期后残留画面当live。PID/start_ticks/停止条件写在CURRENT与retained-processes.json。
- 关闭时先停PC view（使SSH relay退出）、关闭本run RViz，再在Nano正常`bash tools/hardware.sh stop`核验所属进程退出/runtime空/rmem恢复；不要强杀未知控制进程。原Agent76673独立保留，未改其配置。

产物artifacts/runs/hw10-vins-official-view-20261105-030，原生图像/点云校验、GPU证据、路径/图/健康日志与hash清单均保留。029快照仍单列。停止原因：显示修复/原生数据交付与圈观察分析完成，按用户意图保留实时窗口，不启动新算法实验。主线下一项仍HW10-EV-028，027板上高度用户接受通过保持。

[摘要](../../collaboration/dialogues/2026-11-05-030-native-vins-rviz.md)、[改动记录](../changes/2026-11-05-030-native-vins-rviz.md)。

最终检查：project_status结构PASS（251条可选历史产物提示保留，不是运行资格）；PC显示脚本/圈记录器py_compile、git diff --check通过，未stage/提交/推送。030实时显示按用户意图保留，圈数据已保存；source控制/飞行未启动。
