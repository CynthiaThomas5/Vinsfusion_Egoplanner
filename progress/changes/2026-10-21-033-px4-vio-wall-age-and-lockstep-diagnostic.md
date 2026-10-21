# 修改与验证记录

- 任务 ID／日期：#033 / 2026-10-21
- 对话摘要：collaboration/dialogues/2026-10-21-033-px4-vio-wall-age-and-lockstep-diagnostic.md
- 修改文件：新增 #388–#390 run manifests 与 progress/evidence/p5-px4-vio-telemetry-wall-age-diagnostic-20261021-388-390.json；更新 progress/CURRENT.md、progress/milestones.json、progress/evidence/README.md、README.md。SITL 输出保存在 artifacts/runs/。
- 行为变化及原因：canonical 源码和阈值没有变化。#384–#387 的三秒低频PX4 receipt 门在低 RTF 下反复失效；隔离 overlay 改为4.0秒后，#389的VIO/map前置条件和5秒联合稳定窗口通过，原三秒规则在同一采样历史中的最长连续合格段为2.843秒。#390通过窗口、收到服务接受、PX4 preflight转真并进入ARM/TAKEOFF；之后 clock mapper 报 clock_mapping_rate_out_of_bounds，映射里程计接收龄达到0.434秒，超过未改的0.3秒门，状态机转LANDING并最终LANDED/未武装。没有发送导航目标，不能据此宣称完成飞行验收。
- 验证类型：静态／SITL。
- 命令与环境：bash -n 检查三份 run-local 脚本；以 d435i-vins:dev（sha256:099ab9afecd28b7354f6d649b3384b1db30c7c973e9b93b03f87aca7ad6f8）运行 no-truth SITL，详见三个 run manifest；解析证据与manifest JSON并核对产物哈希。
- 结果及证据位置：#389 diagnostic gate通过但未调用控制服务；#390服务已接受，PX4桥在外部里程计映射错误后安全降落，最终 disarmed。报告：[progress/evidence/p5-px4-vio-telemetry-wall-age-diagnostic-20261021-388-390.json](../evidence/p5-px4-vio-telemetry-wall-age-diagnostic-20261021-388-390.json)。阶段维持P4/P5/P6 in_progress，GOAL C/D/E仍未验收。
- 未验证与 PROVISIONAL：4.0秒仅是隔离诊断值。#390的clock fit错误没有桥内拟合率或对应 /clock 序列；cause未定。未验证takeoff altitude、ACTIVE、navigation action、障碍绕行、真值误差、重复冷启动、故障注入或长时间负载。既往#385–#387独立/clock probe的离线64样本拟合均在0.849–4.460范围内，没有复现越界，但不是#390的桥内同步观测。
- 下一步：在 no-truth baseline 下配对记录 /clock、PX4映射里程计、VINS源戳及拟合窗口，复现并解释 transient；保持源龄、里程计龄、alignment 与 preflight fail-closed 门不变。
