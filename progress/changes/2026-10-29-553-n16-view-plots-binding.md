# #553 N16五分钟独立视图/曲线/正式身份入口

Goal完成模式，已应用用户#552最低300sim秒，继续工作而非仅改计划。新增prepare_n16_evaluation.py独立派生视图，原始归档只读引用，地图数组复制以保持原hash与路径检查；复用完整odometry和逐目标独立到达、N16核心证据入口，输出正式身份评估。新增plot_n16_run.py输出真实CPU核使用/内存/native队列/源到回执age曲线及VIO位置/yaw误差和实际运动曲线，图例明确观测口径，不把遥测age冒充已证明的控制因果延迟上界。

新增evaluate_n16_formal.py绑定配置/协议发布、评估器source SHA、实际runtime/世界/goal profile、n16启动记录、核心观察器身份、进程观察器source/run身份、GUI、唯一PX4发布者/无在线真值及图像manifest hash；缺数据和未发布保持INSUFFICIENT，真实证据失败保留FAIL。process recorder加入run_id/source SHA字段。当前配置与协议仍draft，尚未正式运行，不能计通过。

验证：以真实N14短归档实际运行独立完整管线，errors=[]、core/formal不足，实际生成两张测量PNG，原始报告未覆盖；27项相关测试PASS（#552时长/连续/资源/接触/独立到达）；新增代码py_compile、project_status、git diff --check。产物artifacts/reanalysis/n16-20261029-553-formal-negative，图及manifest在其run目录。

未解：隔离候选/多目标外部runner/长时观察器/发布身份集成、实际GUI300秒运行、完整正式审计与端到端时序观测口径补充。下一步隔离部署真实跑验证，不将短数据计时长；N16仍in_progress。对话collaboration/dialogues/2026-10-29-553-n16-pipeline.md。
