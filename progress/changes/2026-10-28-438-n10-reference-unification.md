# N10.3/#438：离线参考与归档复算交付

变更：共用model→IMU读取器、统一PRESTREAM锚点、arrival/odometry/velocity/full-route/cross-run/tracking/clearance/snapshot/replan/acceptance接入；velocity区分运动/保持/降落；记录器写明raw语义；区间评估不再把平滑twist当瞬时端点而判通过。新增来源绑定/重复转换/锚点/混合旧报告/刚体不变性/分段测试。docs/contracts和N10计划标明历史量化结论的更正边界，无数值/控制/模型/第三方变更。

实际复算#381/#385/#436，原始222文件SHA不变，三份各自绑定runtime/输入/参考PASS；#385到达保留、#381不足保留，#436总体INSUFFICIENT。完整数值/哈希见../evidence/n10-reference-unification-20261028-438.md和json。原阈值未变，未新飞；不计N15/N16。

验证：bash tools/project.sh test：576单测+两ROS集成PASS；相关定向测试和py_compile通过。python3 tools/project_status.py、git diff --check收尾核验。未构建ROS/PX4：本轮仅离线Python/记录元数据变化，不替代N10.5。产物artifacts/reanalysis/n10-20261028-438-reference-unification（源快照/工具冻结、原归档完整性、pipeline和测试日志）。

限制：RPE10/hold速度仍越草案；连续界缺瞬时状态/有效上界；tracking总误差预算、重规划和资源/队列量化依据及#437正常现场回归未齐。新增MCAP静止IMU=world g=9.8、实际VINS g_norm9.80665证据，不是根因证明。下一#439同bag只改g_norm离线VINS回放，按结果决定修复；不直接改参数或门限。

停止原因：当前#438子项完成；N10.3/父N10保持in_progress。无活动飞行，未推送。对话：../../collaboration/dialogues/2026-10-28-438-n10-reference-unification.md。
