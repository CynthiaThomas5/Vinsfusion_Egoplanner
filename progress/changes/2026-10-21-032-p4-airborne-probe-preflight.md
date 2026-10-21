# GOAL C 空中机体包络复测前置门诊断 #384–#387

关联对话：[2026-10-21-032](../../collaboration/dialogues/2026-10-21-032-p4-airborne-probe-preflight.md)。

为解决 #383 模型碰撞 AABB 低于地图 z 下界的问题，启动四轮 no-truth SITL 探针：第二障碍布局与 0.5 m 膨胀 #384、相同布局与默认 0.099 m 膨胀／0.5 m 短目标 #385、无附加障碍且启用只读样条观察器 #386、同基线关闭观察器 #387。未修改 canonical 源码或参数。容器镜像 d435i-vins:dev 当前摘要为 sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8；每轮 run-manifest.json 保存脚本、输入配置、相关源码树与关键输出哈希。

四轮都满足 VIO/map 初始化前置条件，但定位与 PX4 遥测未连续稳定 5 秒，导航探针报告 localization_or_px4_freshness_not_stable_before_enable。PX4 状态中 pre_flight_checks_pass 为 0/35、0/38、0/37、0/37。四轮的 span RTF 为 0.291–0.302；estimator_flags 与 land_detected 接收间隔中位数为 3.30–3.42 秒。对照历史 #200 的 RTF 0.641 与相同遥测中位间隔约 1.53 秒。无附加障碍且关闭观察器的 #387 仍失败，故本次证据没有支持障碍布局或采集器导致退化的解释；因果根因仍未确定。

每轮均未调用 EnableOffboard、未派发导航目标、未输出控制样本，车辆保持解除武装。PX4 输入控制话题各只有 uav_px4_bridge 一个发布者。PX4 日志含 ekf2 missing data 与 system power unavailable 警告；历史 #200 也含相同初始警告，因此不能单独用来定位差异。三轮只读样条观察均未收到曲线，故没有空中位姿、同刻地图快照或新机体包络数据。所有结果仅作 fail-closed 诊断，不能用于 P4、P5 或 GOAL C 通过判断。

验证：四轮 Docker SITL 均退出并清理容器；所有 run-local shell 脚本通过 bash -n；报告与运行清单的 JSON 均可解析，产物哈希已记录；控制样本计数全为零且车辆保持 disarmed。下一步先调查并恢复 PX4 状态与仿真时钟稳定度，不下调 freshness 或 preflight 门，再复测同 epoch 空中包络。证据：[汇总报告](../evidence/p5-vio-ego-airborne-preflight-diagnostic-20261021-384-387.json)。
