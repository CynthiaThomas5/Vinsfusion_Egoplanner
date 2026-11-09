# GS02.3 静止 RViz 绘制基线

关联对话：[2026-11-07-003](../../collaboration/dialogues/2026-11-07-003-gs02-static-rviz-paint.md)。新增证据：[静止RViz绘制](../evidence/gs02-static-rviz-paint-20261107.md)。

## 子项与范围

- Goal完成模式，GS02.1–GS02.4；当前子项`GS02.3-static-rviz-paint-baseline`。
- 用户暂时离开，授权先完成不需要现场移动/观察的工作；本轮只做静止纯感知与窗口采集，不移动设备，不启动EV/control或PX4动作。
- 缺口：此前动态reader出现13.2–20.6秒滞后，但尚未直接确认RViz客户窗口是否实际绘制。

## 实际结果

- 从Debian固定入口运行`hw10-groundstation-20261106T085810Z`，285.767秒，1659个位姿；1231条状态样本中1012条有效TRACKING。静止reader发送到读取延迟P95为156–220ms、最大506–865ms；history/image合计4次接收间隔略超1秒，最大1.061秒；没有复现动态长滞后。
- 对RViz客户窗口做30秒/5Hz采样，150帧全窗口像素帧均不同，主3D区域每个采样间隔均出现像素变化；截图可见左右目特征、稀疏点、机体姿态和轨迹。RViz状态栏约15fps。源30秒视频分析后删除，只保留一帧截图、可复核指标、Nano和Debian原始reader/状态记录。
- cgroup无OOM/CPU限流；viewer峰值RSS约193MB；`experiment-stop`正常停止。Nano统一会话、VINS/localization/relay停止，`rmem_max`恢复212992，Agent保持active；没有EV/control/飞控更改。
- 原始run `RUN-SHA256SUMS` 27项通过，manifest SHA256 `37b7969fa9917d42cf2b5b08d76c9eec9790403c575b3610d86add6e22365eb3`。
- 新migration overlay包含165个唯一文件；最终SHA256记录于freeze01 `manifest.json`；Debian目标release 380项、该run 27项、网络run 5项清单通过。目标`python3 tools/project_status.py`、`uav-groundstation check/status`通过，固定镜像SHA未变。
- Debian目标时钟报告`NTP=yes`但`NTPSynchronized=no`，UTC较当前执行环境慢约8小时；本轮未调整系统时钟，运行间隔按monotonic及run内偏移估计解释。

## 验证、局限与交接

- 静止屏幕绘制基线已实证，但不代表动态图像连续性、也不解释运动期间Nano发送后至Debian reader的长滞后；GS02.3与父GS02保持未通过。
- 无需用户操作的工作已停止在动态条件前。下一项待用户回来：短时慢速移动，操作员同步观察画面并报告停顿，以既有资源/NIC/视觉事件采样关联根因；不重复静止run，不改阈值。
- 本轮改动为证据、状态文档和冻结overlay，不改源码/参数。停止原因：运动与现场画面观察需要用户现场协助；设备已安全停止。
