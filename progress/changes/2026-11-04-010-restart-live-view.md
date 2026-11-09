# 按用户要求重启实时会话

对话：[摘要](../../collaboration/dialogues/2026-11-04-010-restart-live-view.md)。无源码/配置修改。核对旧PC PID4796/4797后SIGINT停止；Nano原工作区bash tools/hardware.sh stop正常关闭02，再bash tools/hardware.sh start perception --run-id hardware-live-20261104-03。PC预热只读hardware_live_rviz.py --live --vins-only（run-path指向新03）及rviz2 -d config/rviz/hardware_live.rviz。

验证：15安装模块内容预检通过；fresh epoch381a688a74c44bec8abda3b2183d5fe4、LIVE/TRACKING，2秒间隔轨迹增长；PC唯一view7268/RViz7269、无回放。证据artifacts/runs/hardware-live-20261104-03/verified-status.json和日志；结构/diff检查通过。未重启设备、未改参数、未运行EV/控制或新增飞行资格。

停止原因：重启请求完成，依用户要求保留活动显示会话；PID及退出/rmem恢复条件见CURRENT。未修复或关闭HW10既有时序问题，下一功能任务仍HW10.3；未提交/推送。
