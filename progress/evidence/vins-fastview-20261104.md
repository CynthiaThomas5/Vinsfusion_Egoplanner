# VIS12 实时显示链路优化

范围：四类可视化及传播位姿机体显示。结果：本轮显示优化完成；不更新HW08/HW10资格。新会话hardware-fastview-20261104-02，epoch8cc66234464241119df05b6792e3cea7。

## 前后证据

修改前约21.20s PC实测：image1.04、points1.13、history0.94、camera1.13Hz。对应只读核对保存于本轮baseline-rate-check文本；旧报告VIS11显示四类真实可用，但不能把设置上限当实际刷新率。

修改后display-samples.jsonl：59.749s、150次定时采样，150/150有效。实际PC接收并通过显示源龄检查的速率body9.724、image3.414、points4.787、camera4.820、history1.724Hz；解码错误0。显示上限body20、image5、camera/points10、history2Hz均不是性能保证。传播位姿用于显示机体，粉色轨迹继续使用优化结果。

源采样到PC处理（中位/P95）：body65/350ms；image378/929ms；points396/586ms；camera390/610ms。body远程发送前龄中位8.5ms，image255ms，说明机体更及时，但图像前端仍有耗时，网络/调度仍有抖动。记录中的image最大2.077s为被显示过旧检查丢弃的样本，非成功发布。统计按约0.4s定时抽样，重复最近消息的指标，非每包独立分位数。完整数字见display-summary.json。

跨机时钟经已建立SSH连接5次ping，最短RTT/2约0.681ms作为探测误差参考；非严格硬件同步误差界，网络非对称和后续时钟漂移未排除。统计只到PC处理，未测RViz渲染/屏幕延迟。未用旧Nano日历直接减PC日历。

health-summary.json：73.026s 72条健康观察，前2条初始化，后70条有效，最后TRACKING。截图rviz-verified.png可见真实JPEG双目预览、点云和机体轴，Global Status OK。独立5s /proc CPU差分：image relay10.5%、geometry24.1%，VINS138.2%、adapter85.7%、相机23.9%；采样匹配进程合计282.4%（四核400%，未包含其他系统进程），非长期满载资格。原始图像/算法配置未降采样，只有PC预览缩为640×240 JPEG65。

## 运行与检查

首次fastview01在相机检查阶段退出141，尚未启动VINS。hardware.sh两个printf|awk首值提取提前exit可导致大枚举输入pipefail/SIGPIPE，改为读完输入保持首值；1MB回归验证通过。失败日志保留，等待manifest的两个relay已显式清理；新02启动成功并接管两路relay身份。旧visuals01正常关闭，停机阶段报告过imu_future_source_stamp，既有时序风险未解决，不外推本轮短观察。

定向命令：source /opt/ros/humble/setup.bash；python3 tools/test_hardware_live_view.py、tools/test_vins_visual_transport.py；python3 tools/test_hardware_session.py（5项）；四脚本py_compile、bash -n tools/hardware.sh，均PASS。python3 tools/project_status.py结构PASS，git diff --check通过。实际ARM/Foxy relay启动与Humble RViz验证，不是仅结构检查；无包源码改动，无全量构建/SITL/EV/飞行。

PC view17163/RViz17370保持活动；Nano geometry368538/image368537由统一session接管，rmem8388608。停止和恢复212992步骤见CURRENT。活动健康快照独立复制verified-status.json，固定产物hash见sha256.json；完整运行文件在artifacts/runs/hardware-fastview-20261104-02。未提交/推送。停止原因：本轮显示优化完成，保留用户查看窗口。下一功能项仍HW10.3，长期IMU未来戳/装机/控制资格未解。
