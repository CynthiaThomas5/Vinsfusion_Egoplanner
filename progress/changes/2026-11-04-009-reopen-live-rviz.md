# 重新打开实时RViz（运行记录）

对话：[摘要](../../collaboration/dialogues/2026-11-04-009-reopen-live-rviz.md)。无源码/参数修改。旧PC进程已退出、Nano旧会话imu_future_source_stamp锁定；按用户新请求，先bash tools/hardware.sh stop正常收尾，再bash tools/hardware.sh start perception --run-id hardware-live-20261104-02。PC source /opt/ros/humble/setup.bash后启动hardware_live_rviz.py --live --vins-only指向新run，并rviz2 -d config/rviz/hardware_live.rviz，激活窗口置前。未启动EV/Agent/控制或改健康门限。

实测新epoch6edae48125bd491f9d05ef13d9f39efd TRACKING，10s内53条显示Odometry约5.53Hz、轨迹增长；证据artifacts/runs/hardware-live-20261104-02/{display-check,verified-status}.json。结构/diff检查通过，仅为显示运行检查，不是新增稳定性/飞行资格。

停止原因：实时窗口请求完成；保留唯一相机/VINS/localization、PC视图和RViz供查看。当前PID/停止/rmem恢复条件见CURRENT。既有IMU未来戳问题仍未修复，下一算法任务仍为HW10.3；本轮未触发新算法探索。
