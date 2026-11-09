# VIS12 降低显示链路延迟

对话：[摘要](../../collaboration/dialogues/2026-11-04-012-vins-fastview.md)。主要假设：同步发送大图拖慢同流几何；唯一主要方案变量为显示传输结构（图像独立JPEG与最新帧发送），判据为真实PC刷新率提升且定位保持有效；附属显示需求用已有传播位姿更新机体。只执行此一方案。

修改relay_vins_visuals.py为两个独立通道，depth1原始订阅+各类单槽+sender；JPEG640×240 quality65，geometry附传播Odometry。vins_visual_transport.py增加JPEG/标准Odometry验证，hardware_live_rviz.py增加PC最新帧槽、20Hz消费、clock probe与源龄指标，传播只用于机体显示，优化保留轨迹。hardware-session.py等待/接管两个relay；hardware.sh修复两处大枚举输入awk提前exit造成pipefail141的风险；docs说明实际限制。

验证命令：source /opt/ros/humble/setup.bash后python3 tools/test_hardware_live_view.py、tools/test_vins_visual_transport.py；python3 tools/test_hardware_session.py（5项含1MB枚举输入）；四脚本py_compile、bash -n tools/hardware.sh。全部通过。实际Nano/Foxy预热与PC/Humble四类显示、传播显示及约60s定向观察通过；project_status.py结构PASS、git diff --check通过。脚本/显示变更未重编译包，未执行全量构建/SITL/控制或飞行。未提交/推送。

第一次fastview01在传感器预检141退出，尚未生成manifest/启动VINS，等待relay显式清理，修复后新02成功；旧visuals01已正常关闭并恢复rmem。PC仅重开RViz恢复图像dock，不重启成功运行的VINS。性能数字、采样限制与文件hash见[证据](../evidence/vins-fastview-20261104.md)。本轮完成并按用户意图保留活动窗口；结束方法和下一项HW10.3见CURRENT。显示成功不改变HW08/HW10未通过状态。
