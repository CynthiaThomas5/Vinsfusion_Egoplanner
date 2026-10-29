# N10.3/#409 准备与观察器解耦

- 对话摘要：`collaboration/dialogues/2026-10-28-409-n10-integrated-calibration.md`
- 产物：`artifacts/n10-prepared/n10-20261028-409-speed040-integrated-calibration/`、`progress/evidence/n10-integrated-calibration-protocol-20261028-409.json`。
- 调整：为 raw/inflated 地图配对和保存 depth ROI 准备离线比较器；从起飞图校验中解除只读 sensor capture subscriber 数量/存在性；移除独立地图点查询 observer 和其飞后等待；观察器启动/manifest 错误改为诊断缺数据；20 仿真秒保持仅针对 #391 漂移起点的诊断采样。
- 验证：26 个定向 Python 单测通过；相关 evaluator/injector/prepare `py_compile`、仿真和 driver `bash -n`、JSON parse、`git diff --check` 通过；安装 VINS binary SHA 对齐 #408 构建记录。
- 限制：#409 SITL 尚未启动；没有飞行证据、故障终态结论、资源限值结论或 N10 通过状态。
- 下一步：按协议启动 #409；飞后评估 arrival、VIO/RPE、tracking、连续净空、replanning、同身份 map pair、queue/resource、sensor stream 和 PX4 终态。
